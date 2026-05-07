import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import settings
from .jobs import store, Job
from .ratelimit import SlidingWindowLimiter
from . import ytdlp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("yt-saver")

app = FastAPI(title="YT Saver", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

limiter = SlidingWindowLimiter(settings.rate_limit_per_hour, 3600)
worker_pool = ThreadPoolExecutor(max_workers=settings.max_concurrent_jobs)


class JobRequest(BaseModel):
    url: str
    format: str = Field(pattern="^(mp4|mp3)$")
    quality: str = "auto"


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.on_event("startup")
async def on_startup():
    ok, msg = ytdlp.have_binaries()
    if not ok:
        log.warning("Binary check failed: %s", msg)
    asyncio.create_task(_reaper_loop())


async def _reaper_loop():
    while True:
        await asyncio.sleep(300)
        for job in store.reap(settings.file_ttl_seconds):
            if job.file_path:
                try:
                    Path(job.file_path).unlink(missing_ok=True)
                except Exception:
                    log.exception("Failed to delete %s", job.file_path)


@app.get("/health")
def health():
    ok, msg = ytdlp.have_binaries()
    return {"status": "ok" if ok else "degraded", "detail": msg}


@app.get("/api/info")
def info(url: str, request: Request):
    if not ytdlp.is_youtube_url(url):
        raise HTTPException(400, "Not a valid YouTube URL")
    if not limiter.allow(client_ip(request)):
        raise HTTPException(429, "Rate limit exceeded — try again later")
    try:
        return ytdlp.fetch_info(url)
    except Exception as e:
        log.warning("info failed: %s", e)
        raise HTTPException(502, "Could not fetch video info")


@app.post("/api/jobs")
def create_job(req: JobRequest, request: Request):
    if not ytdlp.is_youtube_url(req.url):
        raise HTTPException(400, "Not a valid YouTube URL")
    if not limiter.allow(client_ip(request)):
        raise HTTPException(429, "Rate limit exceeded — try again later")

    try:
        meta = ytdlp.fetch_info(req.url)
    except Exception as e:
        log.warning("info failed during job create: %s", e)
        raise HTTPException(502, "Could not fetch video info")

    if meta["duration"] > settings.max_duration_seconds:
        raise HTTPException(
            413,
            f"Video too long (max {settings.max_duration_seconds // 60} minutes)",
        )

    job = store.create(req.url, req.format, req.quality)
    store.update(job.id, info=meta)
    worker_pool.submit(_run_job, job.id)
    return {"jobId": job.id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.public()


@app.get("/files/{name}")
def serve_file(name: str):
    safe = Path(name).name  # strip path separators
    path = settings.files_dir / safe
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "File not found or expired")
    media_type = "audio/mpeg" if safe.endswith(".mp3") else "video/mp4"
    return FileResponse(path, media_type=media_type, filename=safe)


def _run_job(job_id: str):
    job = store.get(job_id)
    if not job:
        return
    store.update(job_id, status="processing", progress=0)
    try:
        path = ytdlp.download(
            url=job.url,
            fmt=job.format,
            quality=job.quality,
            out_dir=settings.files_dir,
            job_id=job_id,
            on_progress=lambda pct: store.update(job_id, progress=pct),
        )
        store.update(
            job_id,
            status="ready",
            progress=100,
            file_path=str(path),
            finished_at=time.time(),
        )
    except Exception as e:
        log.exception("Job %s failed", job_id)
        store.update(job_id, status="error", error=str(e), finished_at=time.time())
