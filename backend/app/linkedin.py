"""Parse candidate-provided professional LinkedIn exports. No network access."""
import csv
import io
import re
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Dict, List

from fastapi import HTTPException

from .resumes import extract_resume

MAX_UPLOAD = 5 * 1024 * 1024
MAX_EXPANDED = 20 * 1024 * 1024
MAX_ENTRIES = 200
MAX_TEXT = 100_000
MAX_ROWS = 2000
MAX_FIELD = 20_000

# Strict file and column allow-lists. Profile.csv can contain contact/address/birth
# information: those columns are never retained. Unrelated archive files are ignored.
CSV_SECTIONS = {
    "profile": ("Summary", {"headline", "summary", "industry"}),
    "positions": ("Experience", {"companyname", "title", "description", "startedon", "finishedon"}),
    "skills": ("Skills", {"name", "skill"}),
    "projects": ("Projects", {"title", "name", "description", "startedon", "finishedon"}),
    "education": ("Education", {"schoolname", "degree", "notes", "fieldofstudy", "startdate", "enddate"}),
    "certifications": ("Certifications", {"name", "authority", "startedon", "finishedon"}),
    "courses": ("Courses", {"name", "associatedwith"}),
    "publications": ("Publications", {"name", "title", "publisher", "description", "publisheddate"}),
    "patents": ("Patents", {"title", "description", "issuer", "issuedon"}),
    "volunteering": ("Volunteering", {"organization", "role", "description", "startedon", "finishedon"}),
    "volunteerexperience": ("Volunteering", {"organization", "role", "description", "startedon", "finishedon"}),
    "honors": ("Honors", {"title", "description", "issuer", "issuedon"}),
    "honorsandawards": ("Honors", {"title", "description", "issuer", "issuedon"}),
}
CONTACT = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?<!\w)(?:\+\d{1,3}[ -]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)|(?<!\w)\+?\d{10,15}(?!\w)|(?<!\w)(?:\+?\d{1,3}[ -]?)?\d{5}[ -]\d{5}(?!\w)")
PRIVATE_LINE = re.compile(r"^\s*(?:first name|last name|full name|name|email|e-mail|phone|telephone|address|date of birth|birth date|birthday|dob|gender|religion|nationality|marital status|age|connections?|messages?|contacts?)\s*[:=]", re.I)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _safe_filename(filename: str) -> str:
    if not isinstance(filename, str) or not filename or len(filename) > 300:
        raise HTTPException(400, "Choose a LinkedIn export file.")
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    if not name or name.startswith("."):
        raise HTTPException(400, "Choose a valid LinkedIn export filename.")
    return name[:160]


def _decode(data: bytes) -> str:
    try:
        text = data.decode("utf-16") if data.startswith((b"\xff\xfe", b"\xfe\xff")) else data.decode("utf-8-sig")
    except UnicodeError:
        raise HTTPException(400, "Export text must use UTF-8 or BOM-marked UTF-16 encoding.")
    if "\x00" in text:
        raise HTTPException(400, "This export contains binary data instead of readable text.")
    return text


def _clean_text(text: str) -> str:
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw).strip()
        if not line or PRIVATE_LINE.search(line):
            continue
        lines.append(CONTACT.sub("[contact removed]", line))
    result = "\n".join(lines).strip()
    if len(result) > MAX_TEXT:
        raise HTTPException(413, "The professional export text exceeds 100,000 characters. Upload a smaller selection.")
    return result


def _csv(filename: str, data: bytes) -> Dict[str, object]:
    configuration = CSV_SECTIONS.get(_normalized(PurePosixPath(filename).stem))
    if not configuration:
        raise HTTPException(400, "Choose a professional LinkedIn CSV such as Profile, Positions, Skills or Projects; contacts and messages are excluded.")
    section, allowed = configuration
    try:
        reader = csv.reader(io.StringIO(_decode(data), newline=""), strict=True)
        headers = next(reader)
        if not headers or len(headers) > 100 or any(len(header) > 200 for header in headers):
            raise ValueError("Invalid CSV header")
        normalized = [_normalized(header) for header in headers]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate CSV headers")
        selected = [index for index, key in enumerate(normalized) if key in allowed]
        if not selected:
            raise HTTPException(400, "This CSV has no supported professional columns for its filename.")
        lines: List[str] = []
        total = 0
        for row_number, row in enumerate(reader, 1):
            if row_number > MAX_ROWS:
                raise HTTPException(413, "A professional CSV may contain at most 2,000 rows.")
            if not row or not any(value.strip() for value in row):
                continue
            if len(row) != len(headers):
                raise ValueError("CSV row does not match header")
            if any(len(value) > MAX_FIELD for value in row):
                raise HTTPException(413, "An export field exceeds 20,000 characters.")
            for index in selected:
                value = _clean_text(row[index])
                if value:
                    # Standalone values preserve identical work statements for deduplication.
                    lines.append(value)
                    total += len(value) + 1
            if total > MAX_TEXT:
                raise HTTPException(413, "The professional export text is too long.")
    except HTTPException:
        raise
    except (csv.Error, ValueError, StopIteration):
        raise HTTPException(400, "This CSV is malformed. Upload the original professional CSV from your LinkedIn export.")
    result = _clean_text("\n".join(lines))
    return {"text": (section + "\n" + result) if result else "", "section": section}


def _zip(data: bytes) -> Dict[str, object]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise HTTPException(413, "The export ZIP may contain at most 200 entries.")
            expanded, seen, selected = 0, set(), []
            for item in entries:
                name = item.filename
                path = PurePosixPath(name)
                if (not name or "\x00" in name or "\\" in name or path.is_absolute()
                        or ":" in name or any(part in {".", ".."} for part in name.split("/"))):
                    raise HTTPException(400, "The export ZIP contains an unsafe path.")
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise HTTPException(400, "Export ZIP symlinks are not supported.")
                if item.flag_bits & 1:
                    raise HTTPException(400, "Encrypted export ZIP files are not supported.")
                if item.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                    raise HTTPException(400, "Use a standard ZIP or deflated ZIP export.")
                expanded += item.file_size
                if expanded > MAX_EXPANDED:
                    raise HTTPException(413, "The expanded export ZIP must be no larger than 20 MB.")
                key = name.casefold()
                if key in seen:
                    raise HTTPException(400, "The export ZIP contains duplicate file paths.")
                seen.add(key)
                if not item.is_dir() and path.suffix.lower() == ".csv" and _normalized(path.stem) in CSV_SECTIONS:
                    selected.append(item)
            if not selected:
                raise HTTPException(400, "This ZIP has no supported professional CSV files. Connections, messages, contacts and other unrelated files are excluded.")
            texts, sections, read_bytes = [], [], 0
            for item in selected:
                # Never extract members to disk. Bound reads independently of ZIP metadata.
                with archive.open(item, "r") as member:
                    content = member.read(MAX_EXPANDED - read_bytes + 1)
                read_bytes += len(content)
                if read_bytes > MAX_EXPANDED or len(content) != item.file_size:
                    raise HTTPException(413, "The expanded export ZIP exceeded its safe size limit.")
                parsed = _csv(PurePosixPath(item.filename).name, content)
                if parsed["text"]:
                    texts.append(parsed["text"])
                    if parsed["section"] not in sections:
                        sections.append(parsed["section"])
                if sum(len(value) for value in texts) > MAX_TEXT:
                    raise HTTPException(413, "The professional export text exceeds 100,000 characters.")
            return {"text": _clean_text("\n\n".join(texts)), "sections": sections}
    except HTTPException:
        raise
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, ValueError, EOFError, OSError):
        raise HTTPException(400, "This ZIP could not be read. Upload an unencrypted original LinkedIn data export.")


def parse_linkedin_export(filename: str, data: bytes) -> Dict[str, object]:
    """Return only extracted professional text/metadata, never original upload bytes."""
    name = _safe_filename(filename)
    if not data:
        raise HTTPException(400, "The LinkedIn export is empty.")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "LinkedIn export files must be no larger than 5 MB.")
    suffix = PurePosixPath(name).suffix.lower()
    if suffix == ".zip":
        parsed = _zip(data)
        text, sections = parsed["text"], parsed["sections"]
    elif suffix == ".csv":
        parsed = _csv(name, data)
        text, sections = parsed["text"], [parsed["section"]]
    elif suffix == ".pdf":
        text, _ = extract_resume(name, data)
        text, sections = _clean_text(text), ["Profile document"]
    elif suffix == ".txt":
        text, sections = _clean_text(_decode(data)), ["Profile text"]
    else:
        raise HTTPException(400, "Upload your own LinkedIn profile PDF, TXT, professional CSV or data-export ZIP.")
    if not text.strip() or (suffix in {".pdf", ".txt"} and len(text.strip()) < 20):
        raise HTTPException(400, "Not enough readable professional text was found. Upload a text-bearing profile PDF or professional export.")
    return {"status": "available", "type": "candidate_export", "filename": name,
            "text": text, "sections": sections,
            "detail": "Professional content extracted from a candidate-provided LinkedIn export. Identity, employment and claims are self-reported and unverified. Contact and unrelated ZIP files were excluded. The original uploaded file is not retained.",
            "imported_at": datetime.now(timezone.utc).isoformat()}
