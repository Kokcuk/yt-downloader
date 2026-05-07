import time
import uuid
from dataclasses import dataclass, field, asdict
from threading import Lock
from typing import Any, Optional


@dataclass
class Job:
    id: str
    url: str
    format: str
    quality: str
    status: str = "queued"  # queued | processing | ready | error
    progress: int = 0
    info: dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def public(self) -> dict[str, Any]:
        d = {
            "jobId": self.id,
            "status": self.status,
            "progress": self.progress,
            "info": self.info,
        }
        if self.status == "ready" and self.file_path:
            ext = "mp3" if self.format == "mp3" else "mp4"
            d["downloadUrl"] = f"/files/{self.id}.{ext}"
        if self.status == "error":
            d["error"] = self.error
        return d


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()

    def create(self, url: str, format: str, quality: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], url=url, format=format, quality=quality)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                setattr(job, k, v)

    def reap(self, ttl_seconds: int) -> list[Job]:
        now = time.time()
        expired: list[Job] = []
        with self._lock:
            for jid, job in list(self._jobs.items()):
                anchor = job.finished_at or job.created_at
                if now - anchor > ttl_seconds:
                    expired.append(job)
                    self._jobs.pop(jid, None)
        return expired


store = JobStore()
