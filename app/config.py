from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: Path = Path("storage")
    upload_dir: Path = Path("storage/uploads")
    results_dir: Path = Path("storage/results")
    max_upload_size_mb: int = 100
    grobid_url: str = "http://localhost:8070"
    tesseract_cmd: str = "tesseract"
    allowed_mime_types: list[str] = ["application/pdf"]

    model_config = {"env_prefix": "PDF_"}


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.results_dir.mkdir(parents=True, exist_ok=True)
