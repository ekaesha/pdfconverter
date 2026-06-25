from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import uuid


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    completed_with_warnings = "completed_with_warnings"
    partial = "partial"
    failed = "failed"
    failed_validation = "failed_validation"


class OcrMode(str, Enum):
    auto = "auto"
    force = "force"
    off = "off"


class JobCreateParams(BaseModel):
    extract_tables: bool = True
    extract_images: bool = True
    extract_formulas: bool = True
    ocr_mode: OcrMode = OcrMode.auto
    output_formats: list[str] = Field(default=["json", "md"])
    language_hint: str = "en"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    pages_total: Optional[int] = None
    pages_done: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class FormulaResult(BaseModel):
    page: int
    bbox: list[float]
    latex: str
    confidence: float


class TableResult(BaseModel):
    page: int
    bbox: list[float]
    markdown: str
    csv_path: Optional[str] = None


class FigureResult(BaseModel):
    page: int
    bbox: list[float]
    image_path: str


class ReferenceResult(BaseModel):
    raw: str
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None


class PageResult(BaseModel):
    page: int
    text: str
    markdown: str = ""
    confidence: float = 1.0


class SectionResult(BaseModel):
    title: str
    level: int
    text: str
    pages: list[int] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    doi: Optional[str] = None


class DocumentResult(BaseModel):
    document_id: str
    source: dict
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    sections: list[SectionResult] = Field(default_factory=list)
    formulas: list[FormulaResult] = Field(default_factory=list)
    tables: list[TableResult] = Field(default_factory=list)
    figures: list[FigureResult] = Field(default_factory=list)
    references: list[ReferenceResult] = Field(default_factory=list)
    pages: list[PageResult] = Field(default_factory=list)
    diagnostics: dict = Field(default_factory=dict)
