import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.schemas.job import JobCreateParams, JobStatusResponse, OcrMode
from app.job_store import job_store
from app.celery_app import process_pdf_task

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.post("", response_model=JobStatusResponse)
async def create_job(
    file: UploadFile = File(...),
    extract_tables: bool = Form(True),
    extract_images: bool = Form(True),
    extract_formulas: bool = Form(True),
    ocr_mode: OcrMode = Form(OcrMode.auto),
    language_hint: str = Form("en"),
):
    if file.content_type not in settings.allowed_mime_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(413, f"File too large: {size_mb:.1f}MB (max {settings.max_upload_size_mb}MB)")

    job_id = str(uuid.uuid4())
    job_dir = settings.upload_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = job_dir / file.filename
    pdf_path.write_bytes(content)

    params = JobCreateParams(
        extract_tables=extract_tables,
        extract_images=extract_images,
        extract_formulas=extract_formulas,
        ocr_mode=ocr_mode,
        language_hint=language_hint,
    )
    status = job_store.create(job_id, file.filename, params)

    process_pdf_task.delay(job_id)

    return status


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    status = job_store.get(job_id)
    if not status:
        raise HTTPException(404, "Job not found")
    return status


@router.get("/{job_id}/result.json")
async def get_result_json(job_id: str):
    result_path = settings.results_dir / job_id / "result.json"
    if not result_path.exists():
        raise HTTPException(404, "Result not ready")
    return FileResponse(result_path, media_type="application/json")


@router.get("/{job_id}/result.md")
async def get_result_md(job_id: str):
    result_path = settings.results_dir / job_id / "result.md"
    if not result_path.exists():
        raise HTTPException(404, "Result not ready")
    return FileResponse(result_path, media_type="text/markdown")


@router.get("/{job_id}/artifacts.zip")
async def get_artifacts(job_id: str):
    result_dir = settings.results_dir / job_id
    zip_path = result_dir / "artifacts.zip"
    if not zip_path.exists():
        raise HTTPException(404, "Artifacts not ready")
    return FileResponse(zip_path, media_type="application/zip")


@router.post("/{job_id}/retry", response_model=JobStatusResponse)
async def retry_job(job_id: str):
    raw = job_store.get_raw(job_id)
    if not raw:
        raise HTTPException(404, "Job not found")

    job_store.update(job_id, status="queued", progress=0.0, pages_done=None, warnings=[], error=None)
    process_pdf_task.delay(job_id)

    return job_store.get(job_id)


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    if not job_store.delete(job_id):
        raise HTTPException(404, "Job not found")

    upload_dir = settings.upload_dir / job_id
    result_dir = settings.results_dir / job_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    if result_dir.exists():
        shutil.rmtree(result_dir)

    return {"status": "deleted"}
