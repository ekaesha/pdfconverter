import fitz  # PyMuPDF


def inspect_pdf(pdf_path: str) -> dict:
    """Determine if PDF is born-digital or scanned, and gather basic info."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    text_pages = 0
    total_chars = 0

    for page in doc:
        text = page.get_text()
        char_count = len(text.strip())
        total_chars += char_count
        if char_count > 50:
            text_pages += 1

    doc.close()

    born_digital = text_pages > total_pages * 0.5

    return {
        "total_pages": total_pages,
        "text_pages": text_pages,
        "total_chars": total_chars,
        "born_digital": born_digital,
    }
