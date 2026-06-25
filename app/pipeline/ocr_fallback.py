from pathlib import Path

import pytesseract
from PIL import Image

from app.schemas.job import PageResult


def ocr_pages(rasterized_paths: list[Path], language: str = "eng") -> list[PageResult]:
    """Run Tesseract OCR on rasterized page images."""
    pages = []

    for i, img_path in enumerate(rasterized_paths):
        try:
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img, lang=language)
            data = pytesseract.image_to_data(img, lang=language, output_type=pytesseract.Output.DICT)

            confidences = [int(c) for c in data["conf"] if int(c) > 0]
            avg_conf = sum(confidences) / len(confidences) / 100 if confidences else 0.0

            pages.append(PageResult(
                page=i + 1,
                text=text,
                markdown=text,
                confidence=round(avg_conf, 2),
            ))
        except Exception as e:
            pages.append(PageResult(
                page=i + 1,
                text="",
                markdown="",
                confidence=0.0,
            ))

    return pages
