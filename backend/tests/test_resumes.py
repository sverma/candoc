import io
import pytest
from fastapi import HTTPException
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from app.resumes import extract_resume

TEXT = 'Built Python services with PostgreSQL and improved API latency by 35 percent.'


def make_pdf(encrypted=False, pages=1):
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    font_reference = writer._add_object(font)
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font_reference})})
        content = DecodedStreamObject()
        content.set_data(('BT /F1 12 Tf 50 700 Td (' + TEXT + ') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(content)
    if encrypted:
        writer.encrypt('secret')
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_valid_pdf_extracts_actual_text():
    extracted, suffix = extract_resume('resume.pdf', make_pdf())
    assert TEXT in extracted
    assert suffix == '.pdf'


def test_valid_docx_reads_paragraphs_and_tables():
    document = Document()
    document.add_paragraph(TEXT)
    document.add_table(rows=1, cols=1).cell(0, 0).text = 'Created deployment pipelines with Docker.'
    output = io.BytesIO()
    document.save(output)
    extracted, suffix = extract_resume('resume.docx', output.getvalue())
    assert TEXT in extracted
    assert 'deployment pipelines' in extracted
    assert suffix == '.docx'


def test_utf8_txt_handles_bom_and_control_characters():
    extracted, suffix = extract_resume('RESUME.TXT', ('\ufeff' + TEXT + '\x07').encode('utf-8'))
    assert extracted == TEXT
    assert suffix == '.txt'


@pytest.mark.parametrize('data', [make_pdf(encrypted=True), make_pdf(pages=51)])
def test_encrypted_and_excessive_page_pdf_rejected(data):
    with pytest.raises(HTTPException) as error:
        extract_resume('resume.pdf', data)
    assert error.value.status_code == 400
