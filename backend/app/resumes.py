import io
import re
import zipfile
from pathlib import Path
from fastapi import HTTPException

MAX_UPLOAD = 5 * 1024 * 1024
MAX_TEXT = 100000


def extract_resume(filename, data):
    suffix = Path(filename.replace('\\', '/')).suffix.lower()
    if suffix not in {'.pdf', '.docx', '.txt'}:
        raise HTTPException(400, 'Upload a PDF, DOCX, or UTF-8 TXT resume.')
    if not data:
        raise HTTPException(400, 'The uploaded file is empty.')
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, 'Resume files must be no larger than 5 MB.')
    try:
        if suffix == '.pdf':
            from pypdf import PdfReader
            if not data.startswith(b'%PDF-'):
                raise ValueError('not a PDF')
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError('encrypted')
            if len(reader.pages) > 50:
                raise HTTPException(400, 'Resume PDFs must contain 50 pages or fewer.')
            chunks = []
            total = 0
            for page in reader.pages:
                part = page.extract_text() or ''
                total += len(part)
                if total > MAX_TEXT:
                    raise HTTPException(400, 'Resume text is too long. Please upload a shorter document.')
                chunks.append(part)
            text = '\n'.join(chunks)
        elif suffix == '.docx':
            from docx import Document
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                    raise HTTPException(400, 'The expanded document is too large.')
                if len(archive.infolist()) > 500:
                    raise HTTPException(400, 'The document contains too many embedded files.')
            doc = Document(io.BytesIO(data))
            chunks = [paragraph.text for paragraph in doc.paragraphs]
            chunks += [' '.join(cell.text for cell in row.cells) for table in doc.tables for row in table.rows]
            text = '\n'.join(chunks)
        else:
            text = data.decode('utf-8-sig')
            if '\x00' in text:
                raise ValueError('binary text')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, 'This document could not be read. Use an unencrypted PDF, DOCX, or UTF-8 TXT file.')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).strip()
    if len(text) > MAX_TEXT:
        raise HTTPException(400, 'Resume text is too long. Please upload a shorter document.')
    if len(text) < 40:
        raise HTTPException(400, 'Not enough readable text was found. Scanned PDFs need OCR before upload.')
    return text, suffix
