from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.jobs import router as jobs_router

app = FastAPI(
    title="Scientific PDF Converter",
    description="Web service for parsing scientific PDF documents into structured data",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    from app.config import settings
    checks = {
        "storage": settings.storage_dir.exists(),
    }
    ready = all(checks.values())
    return {"ready": ready, "checks": checks}
