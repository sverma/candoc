"""Synthetic candidate exports; no test reads a real profile or calls a network."""
import csv
import io
import stat
import struct
import zipfile

import pytest
from fastapi import HTTPException
from pypdf import PdfWriter

from app import linkedin
from app.evaluation import evaluate_profile


DESCRIPTION = "Built a Python reporting service for client operations teams and improved reliability through pilot testing and research."


def csv_bytes(headers, rows, encoding="utf-8"):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode(encoding)


def zip_bytes(files, compression=zipfile.ZIP_DEFLATED):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        for name, content in files:
            archive.writestr(name, content)
    return stream.getvalue()


def test_professional_csv_allowlist_excludes_identifiers_contacts_birth_and_unrelated_fields():
    data = csv_bytes(["First Name", "Last Name", "Headline", "Summary", "Email", "Birth Date", "Address", "Phone Number", "Gender"],
                     [["Alex", "Example", "Product engineer", DESCRIPTION, "private@example.test", "1980-02-01", "Secret address", "+919876543210", "female"]])
    result = linkedin.parse_linkedin_export("Profile.csv", data)
    assert result["type"] == "candidate_export"
    assert result["status"] == "available"
    assert result["filename"] == "Profile.csv"
    assert result["sections"] == ["Summary"]
    assert DESCRIPTION in result["text"]
    assert "Product engineer" in result["text"]
    assert result["imported_at"]
    for private in ["Alex", "Example", "private@example", "1980-02-01", "Secret address", "9876543210", "female"]:
        assert private not in result["text"]
    assert "self-reported" in result["detail"]
    assert "original" in result["detail"].lower()
    assert all(not isinstance(value, bytes) for value in result.values())


def test_archive_only_professional_files_read_not_connections_messages_contacts(monkeypatch):
    data = zip_bytes([
        ("export/Profile.csv", csv_bytes(["Headline", "Summary"], [["Product engineer", DESCRIPTION]])),
        ("export/Positions.csv", csv_bytes(["Company Name", "Title", "Description", "Location", "Phone"], [["Example Tools", "Engineer", DESCRIPTION, "Private home", "9876543210"]])),
        ("export/Skills.csv", b"Name\nPython\nSQL\n"),
        ("export/Connections.csv", b"Email Address\nprivateconnection@example.test\n"),
        ("export/messages.csv", b"FROM,CONTENT\nfriend,secret message\n"),
        ("export/Email Addresses.csv", b"Email Address\nprivate@example.test\n"),
        ("export/Contacts.csv", b"First Name,Phone\nThird Person,9876543210\n"),
        ("export/random.txt", b"Do not read unrelated content"),
    ])
    original = zipfile.ZipFile.open
    read_members = []
    def checked_open(archive, name, *args, **kwargs):
        read_members.append(name.filename if isinstance(name, zipfile.ZipInfo) else name)
        return original(archive, name, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "open", checked_open)
    result = linkedin.parse_linkedin_export("data.zip", data)
    assert result["sections"] == ["Summary", "Experience", "Skills"]
    assert len(read_members) == 3
    for unwanted in ["privateconnection", "secret message", "private@example", "Third Person", "Do not read", "Private home"]:
        assert unwanted not in result["text"]
    assert not any("Connections" in name or "messages" in name for name in read_members)


def test_only_disallowed_archive_rejected():
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", zip_bytes([("Connections.csv", b"email\nsecret@example.test")]))
    assert exc.value.status_code == 400
    assert "no supported professional" in exc.value.detail


@pytest.mark.parametrize("filename", ["Connections.csv", "messages.csv", "Email Addresses.csv", "Contacts.csv", "unknown.csv"])
def test_unrelated_individual_csv_rejected(filename):
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export(filename, b"Name,Email\nSecret Person,secret@example.test")
    assert exc.value.status_code == 400


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16"])
def test_bom_encodings_and_multiline_description_supported(encoding):
    description = DESCRIPTION + "\nCreated a dashboard for the product team and validated customer workflows."
    data = csv_bytes(["Title", "Description"], [["Engineer", description]], encoding=encoding)
    result = linkedin.parse_linkedin_export("Positions.csv", data)
    assert DESCRIPTION in result["text"]
    assert "Created a dashboard" in result["text"]


def test_short_valid_skill_csv_accepted():
    result = linkedin.parse_linkedin_export("Skills.csv", b"Name\nSQL\n")
    assert result["text"] == "Skills\nSQL"


@pytest.mark.parametrize("data", [
    b'Name\n"Unclosed quotation', b"Name,Skill\nPython,SQL,unexpected", b"Name,Name\nPython,SQL", b"Unrelated\nPrivate value", b"", b"Name\n\xff\xfe\xff",
])
def test_malformed_or_unsupported_csv_rejected(data):
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("Skills.csv", data)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("filename,data,status", [
    ("Profile.txt", b"x" * (5 * 1024 * 1024 + 1), 413),
    ("Profile.txt", b"x" * 100_001, 413),
    ("Profile.txt", b"", 400),
    ("Profile.txt", b"short", 400),
    ("Profile.txt", b"\x00" * 30, 400),
    ("Profile.exe", b"readable professional text" * 2, 400),
    ("Skills.csv", b"Name\n" + b"x" * 20_001, 413),
    ("Skills.csv", b"Name\n" + b"Python\n" * 2001, 413),
])
def test_file_field_row_and_text_limits(filename, data, status):
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export(filename, data)
    assert exc.value.status_code == status


@pytest.mark.parametrize("name", ["../Skills.csv", "/Skills.csv", "nested/../Skills.csv", "nested/./Skills.csv", "C:/Skills.csv", "nested\\Skills.csv"])
def test_archive_traversal_rejected_even_when_not_extracted(name):
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", zip_bytes([(name, b"Name\nPython\n")]))
    assert exc.value.status_code == 400
    assert "unsafe path" in exc.value.detail


def test_zip_symlink_rejected():
    link = zipfile.ZipInfo("Skills.csv")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", zip_bytes([(link, b"/etc/passwd")]))
    assert exc.value.status_code == 400
    assert "symlink" in exc.value.detail


def test_encrypted_zip_flag_rejected_without_trying_password():
    data = bytearray(zip_bytes([("Skills.csv", b"Name\nSQL\n")]))
    local = data.index(b"PK\x03\x04")
    central = data.index(b"PK\x01\x02")
    for offset in (local + 6, central + 8):
        flags = struct.unpack_from("<H", data, offset)[0]
        struct.pack_into("<H", data, offset, flags | 1)
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", bytes(data))
    assert exc.value.status_code == 400
    assert "Encrypted" in exc.value.detail


def test_zip_expansion_bomb_limit_applies_even_to_ignored_files():
    data = zip_bytes([("messages.csv", b"x" * (20 * 1024 * 1024 + 1)), ("Skills.csv", b"Name\nSQL\n")])
    assert len(data) < 5 * 1024 * 1024
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", data)
    assert exc.value.status_code == 413
    assert "20 MB" in exc.value.detail


def test_zip_entry_count_limit_and_bad_zip():
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", zip_bytes([(str(i) + ".txt", b"x") for i in range(201)]))
    assert exc.value.status_code == 413
    with pytest.raises(HTTPException) as exc:
        linkedin.parse_linkedin_export("data.zip", b"not a zip")
    assert exc.value.status_code == 400


def test_no_files_extracted_and_filename_path_sanitized(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Export ZIP must not be extracted to disk")
    monkeypatch.setattr(zipfile.ZipFile, "extract", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    result = linkedin.parse_linkedin_export("../../data.zip", zip_bytes([("Skills.csv", b"Name\nPython\nSQL\n")]))
    assert result["filename"] == "data.zip"


def test_txt_privacy_and_pasted_uploaded_score_parity():
    text = "Summary\n" + DESCRIPTION + "\nEmail: private@example.test\nPhone: +919876543210\nGender: female\nCall 9876543210 for information."
    exported = linkedin.parse_linkedin_export("Profile.txt", text.encode())
    for private in ["private@example", "female", "9876543210"]:
        assert private not in exported["text"]
    pasted = evaluate_profile("", ["Python"], linkedin_text=exported["text"])
    uploaded = evaluate_profile("", ["Python"], linkedin_data=exported)
    assert pasted["score"] == uploaded["score"]
    assert [d["score"] for d in pasted["dimensions"]] == [d["score"] for d in uploaded["dimensions"]]


def test_pdf_reuses_bounded_existing_parser(monkeypatch):
    calls = []
    def parse(name, data):
        calls.append((name, data))
        return "Summary\n" + DESCRIPTION, ".pdf"
    monkeypatch.setattr(linkedin, "extract_resume", parse)
    result = linkedin.parse_linkedin_export("LinkedIn.pdf", b"%PDF-test-fixture")
    assert result["sections"] == ["Profile document"]
    assert DESCRIPTION in result["text"]
    assert len(calls) == 1


def test_encrypted_pdf_and_too_many_pages_rejected():
    for encrypted in (True, False):
        writer = PdfWriter()
        for _ in range(1 if encrypted else 51):
            writer.add_blank_page(width=100, height=100)
        if encrypted:
            writer.encrypt("not-accepted")
        stream = io.BytesIO()
        writer.write(stream)
        with pytest.raises(HTTPException) as exc:
            linkedin.parse_linkedin_export("LinkedIn.pdf", stream.getvalue())
        assert exc.value.status_code == 400
