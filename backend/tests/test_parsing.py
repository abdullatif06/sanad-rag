import io

import docx
import pytest

from app.parsing import NoTextError, Page, UnsupportedFileError, parse


def make_pdf(pages: list[str]) -> bytes:
    """Build a tiny valid PDF with one line of text per page."""
    objects = []
    n = len(pages)
    page_ids = [3 + i * 2 for i in range(n)]
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>")
    font_id = 3 + n * 2
    for i, text in enumerate(pages):
        content_id = page_ids[i] + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def make_docx(paragraphs: list[str]) -> bytes:
    d = docx.Document()
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_pdf_keeps_page_numbers():
    pages = parse(make_pdf(["Refund policy is 30 days", "Shipping takes 5 days"]), "policy.pdf")
    assert pages == [
        Page(number=1, text="Refund policy is 30 days"),
        Page(number=2, text="Shipping takes 5 days"),
    ]


def test_pdf_skips_empty_pages():
    pages = parse(make_pdf(["First", " ", "Third"]), "doc.pdf")
    assert [p.number for p in pages] == [1, 3]


def test_docx_is_one_page():
    pages = parse(make_docx(["Hello", "World"]), "notes.docx")
    assert pages == [Page(number=1, text="Hello\nWorld")]


def test_txt_and_md_support_arabic():
    text = "سياسة الاسترجاع ٣٠ يوماً"
    assert parse(text.encode("utf-8"), "ar.txt") == [Page(number=1, text=text)]
    assert parse(b"# Title", "readme.MD") == [Page(number=1, text="# Title")]


def test_unsupported_extension():
    with pytest.raises(UnsupportedFileError):
        parse(b"data", "image.png")


def test_no_text_raises():
    with pytest.raises(NoTextError):
        parse(make_pdf([" "]), "scanned.pdf")
    with pytest.raises(NoTextError):
        parse(b"   \n ", "empty.txt")
