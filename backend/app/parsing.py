"""Turn uploaded files into plain text, keeping page numbers for citations."""

import io
from dataclasses import dataclass
from pathlib import Path

import docx
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class UnsupportedFileError(ValueError):
    pass


class NoTextError(ValueError):
    """The file has no extractable text (e.g. a scanned PDF)."""


@dataclass(frozen=True)
class Page:
    number: int
    text: str


def parse(data: bytes, filename: str) -> list[Page]:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(f"Unsupported file type: {ext or filename}")

    if ext == ".pdf":
        pages = _parse_pdf(data)
    elif ext == ".docx":
        pages = [Page(1, _parse_docx(data))]
    else:
        pages = [Page(1, data.decode("utf-8", errors="replace"))]

    pages = [Page(p.number, p.text.strip()) for p in pages if p.text.strip()]
    if not pages:
        raise NoTextError(f"{filename} has no extractable text")
    return pages


def _parse_pdf(data: bytes) -> list[Page]:
    reader = PdfReader(io.BytesIO(data))
    return [Page(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]


def _parse_docx(data: bytes) -> str:
    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())
