import zipfile
from pathlib import Path

from celery import Celery

from app.config import settings

celery_app = Celery("pdf_converter", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


@celery_app.task(name="process_pdf", bind=True, max_retries=2)
def process_pdf_task(self, job_id: str):
    from app.job_store import job_store
    from app.pipeline.pdf_inspector import inspect_pdf
    from app.pipeline.text_extractor import extract_text_pymupdf, extract_images_pymupdf, rasterize_pages
    from app.pipeline.ocr_fallback import ocr_pages
    from app.pipeline.grobid_client import process_fulltext
    from app.pipeline.table_extractor import extract_tables_camelot
    from app.pipeline.formula_extractor import detect_formula_regions, extract_formulas_pix2tex
    from app.pipeline.normalizer import build_result, save_result_json, save_result_markdown

    raw = job_store.get_raw(job_id)
    if not raw:
        return

    filename = raw["filename"]
    params = raw["params"]
    pdf_path = str(settings.upload_dir / job_id / filename)
    result_dir = settings.results_dir / job_id
    result_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    diagnostics = {"ocr_used": False, "grobid_used": False, "formula_engine": None}

    try:
        job_store.update(job_id, status="processing", progress=0.05)

        # 1. Inspect PDF
        info = inspect_pdf(pdf_path)
        job_store.update(job_id, pages_total=info["total_pages"], progress=0.1)

        # 2. Extract text
        if info["born_digital"] and params.get("ocr_mode") != "force":
            pages = extract_text_pymupdf(pdf_path)
        else:
            rasterized = rasterize_pages(pdf_path, result_dir)
            pages = ocr_pages(rasterized, language=params.get("language_hint", "eng"))
            diagnostics["ocr_used"] = True
            warnings.append("ocr_fallback_used")

        job_store.update(job_id, progress=0.3, pages_done=len(pages))

        # 3. GROBID
        grobid_data = process_fulltext(pdf_path)
        if grobid_data:
            diagnostics["grobid_used"] = True
        else:
            warnings.append("grobid_unavailable")
        job_store.update(job_id, progress=0.5)

        # 4. Tables
        tables = []
        if params.get("extract_tables", True):
            if info["born_digital"]:
                tables = extract_tables_camelot(pdf_path)
            if not tables:
                warnings.append("no_tables_found")
        job_store.update(job_id, progress=0.6)

        # 5. Images
        figures = []
        if params.get("extract_images", True):
            figures = extract_images_pymupdf(pdf_path, result_dir)
        job_store.update(job_id, progress=0.7)

        # 6. Formulas
        formulas = []
        if params.get("extract_formulas", True):
            regions = detect_formula_regions(pdf_path)
            if regions:
                formulas = extract_formulas_pix2tex(pdf_path, regions, result_dir)
                diagnostics["formula_engine"] = "pix2tex"
                low_conf = [f for f in formulas if f.confidence < 0.5]
                if low_conf:
                    low_pages = sorted(set(f.page for f in low_conf))
                    warnings.append(f"low_confidence_formulas_on_pages_{'_'.join(map(str, low_pages))}")
        job_store.update(job_id, progress=0.85)

        # 7. Normalize and save
        result = build_result(
            job_id=job_id,
            filename=filename,
            info=info,
            pages=pages,
            grobid_data=grobid_data,
            tables=tables,
            figures=figures,
            formulas=formulas,
            diagnostics=diagnostics,
        )

        save_result_json(result, result_dir)
        save_result_markdown(result, result_dir)

        # 8. Create artifacts zip
        _create_artifacts_zip(result_dir)

        status = "completed_with_warnings" if warnings else "completed"
        job_store.update(
            job_id,
            status=status,
            progress=1.0,
            pages_done=info["total_pages"],
            warnings=warnings,
        )

    except Exception as e:
        job_store.update(
            job_id,
            status="failed",
            error=str(e),
            warnings=warnings,
        )
        raise


def _create_artifacts_zip(result_dir: Path):
    zip_path = result_dir / "artifacts.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in result_dir.rglob("*"):
            if file == zip_path or file.is_dir():
                continue
            zf.write(file, file.relative_to(result_dir))
