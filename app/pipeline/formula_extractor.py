import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from app.schemas.job import FormulaResult


def detect_formula_regions(pdf_path: str) -> list[dict]:
    """Heuristic detection of formula regions on pages.

    Looks for pages/regions with typical math indicators:
    inline symbols, display-style spacing, equation numbering.
    """
    doc = fitz.open(pdf_path)
    regions = []

    math_pattern = re.compile(r'[∫∑∏∂∇√±≤≥≠≈∞∈∉⊂⊃∪∩]|\\frac|\\int|\\sum|\\prod|\\partial')

    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block.get("type") != 0:
                continue
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")

            if math_pattern.search(block_text) or _looks_like_equation(block_text):
                bbox = block["bbox"]
                regions.append({
                    "page": page_num + 1,
                    "bbox": list(bbox),
                    "block_text": block_text,
                })

    doc.close()
    return regions


def _looks_like_equation(text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if re.match(r'^\(\d+\)$', text.strip()):
        return False
    special = sum(1 for c in text if not c.isalnum() and not c.isspace())
    if len(text) > 0 and special / len(text) > 0.3 and len(text) < 200:
        return True
    return False


def extract_formulas_pix2tex(pdf_path: str, regions: list[dict], output_dir: Path) -> list[FormulaResult]:
    """Crop formula regions and run pix2tex on them."""
    try:
        from pix2tex.cli import LatexOCR
        model = LatexOCR()
    except ImportError:
        return _fallback_formulas(regions)

    doc = fitz.open(pdf_path)
    formulas_dir = output_dir / "formulas"
    formulas_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, region in enumerate(regions):
        page_idx = region["page"] - 1
        if page_idx >= len(doc):
            continue
        page = doc[page_idx]
        bbox = fitz.Rect(region["bbox"])

        clip = page.get_pixmap(clip=bbox, dpi=300)
        img_path = formulas_dir / f"formula_{i + 1}.png"
        clip.save(str(img_path))

        try:
            img = Image.open(img_path)
            latex = model(img)
            results.append(FormulaResult(
                page=region["page"],
                bbox=region["bbox"],
                latex=latex,
                confidence=0.8,
            ))
        except Exception:
            results.append(FormulaResult(
                page=region["page"],
                bbox=region["bbox"],
                latex=region.get("block_text", ""),
                confidence=0.3,
            ))

    doc.close()
    return results


def _fallback_formulas(regions: list[dict]) -> list[FormulaResult]:
    """Return raw text when pix2tex is not available."""
    return [
        FormulaResult(
            page=r["page"],
            bbox=r["bbox"],
            latex=r.get("block_text", ""),
            confidence=0.2,
        )
        for r in regions
    ]
