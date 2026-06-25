import json
import threading
from pathlib import Path
from typing import Optional

from app.config import settings
from app.schemas.job import JobStatus, JobStatusResponse, JobCreateParams


class JobStore:
    """Simple file-based job store. Replace with Postgres for production."""

    def __init__(self):
        self._lock = threading.Lock()
        self._meta_dir = settings.storage_dir / "jobs"
        self._meta_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self._meta_dir / f"{job_id}.json"

    def create(self, job_id: str, filename: str, params: JobCreateParams) -> JobStatusResponse:
        data = {
            "job_id": job_id,
            "status": JobStatus.queued,
            "progress": 0.0,
            "pages_total": None,
            "pages_done": None,
            "warnings": [],
            "error": None,
            "filename": filename,
            "params": params.model_dump(),
        }
        with self._lock:
            self._path(job_id).write_text(json.dumps(data), encoding="utf-8")
        return JobStatusResponse(**data)

    def get(self, job_id: str) -> Optional[JobStatusResponse]:
        p = self._path(job_id)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return JobStatusResponse(**data)

    def get_raw(self, job_id: str) -> Optional[dict]:
        p = self._path(job_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def update(self, job_id: str, **kwargs):
        with self._lock:
            p = self._path(job_id)
            if not p.exists():
                return
            data = json.loads(p.read_text(encoding="utf-8"))
            data.update(kwargs)
            p.write_text(json.dumps(data), encoding="utf-8")

    def delete(self, job_id: str) -> bool:
        p = self._path(job_id)
        if p.exists():
            p.unlink()
            return True
        return False


job_store = JobStore()
