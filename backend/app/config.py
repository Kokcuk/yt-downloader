import os
from pathlib import Path


class Settings:
    files_dir: Path = Path(os.environ.get("FILES_DIR", "/tmp/yt-saver"))
    file_ttl_seconds: int = int(os.environ.get("FILE_TTL_SECONDS", "1800"))
    max_duration_seconds: int = int(os.environ.get("MAX_DURATION_SECONDS", "1800"))
    max_concurrent_jobs: int = int(os.environ.get("MAX_CONCURRENT_JOBS", "2"))
    rate_limit_per_hour: int = int(os.environ.get("RATE_LIMIT_PER_HOUR", "10"))
    cors_origins: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]


settings = Settings()
settings.files_dir.mkdir(parents=True, exist_ok=True)
