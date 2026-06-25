import fitz  # PyMuPDF
from pathlib import Path

from app.schemas.job import PageResult


def extract_text_pymupdf(pdf_path: str) -> list[PageResult]:
    """Extract text from each page using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text")
        markdown = page.get_text("text")  # basic text; GROBID provides structure
        pages.append(PageResult(
            page=i + 1,
            text=text,
            markdown=markdown,
            confidence=1.0 if len(text.strip()) > 50 else 0.3,
        ))

    doc.close()
    return pages


def extract_images_pymupdf(pdf_path: str, output_dir: Path) -> list[dict]:
    """Extract embedded images from PDF."""
    doc = fitz.open(pdf_path)
    figures = []
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    img_count = 0
    for page_num, page in enumerate(doc):
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                img_count += 1
                img_name = f"fig_{img_count}.png"
                img_path = figures_dir / img_name
                pix.save(str(img_path))

                figures.append({
                    "page": page_num + 1,
                    "bbox": list(page.rect),
                    "image_path": f"figures/{img_name}",
                })
            except Exception:
                continue

    doc.close()
    return figures


def rasterize_pages(pdf_path: str, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Rasterize PDF pages to images for OCR fallback."""
    doc = fitz.open(pdf_path)
    raster_dir = output_dir / "rasterized"
    raster_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        img_path = raster_dir / f"page_{i + 1}.png"
        pix.save(str(img_path))
        paths.append(img_path)

    doc.close()
    return paths
