import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)([\w-]{11})"
)


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match((url or "").strip()))


def fetch_info(url: str) -> dict[str, Any]:
    """Run yt-dlp -J to get metadata without downloading."""
    proc = subprocess.run(
        ["yt-dlp", "-J", "--no-playlist", "--no-warnings", url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(_clean_error(proc.stderr) or "Failed to fetch video info")
    data = json.loads(proc.stdout)
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "channel": data.get("uploader") or data.get("channel"),
        "duration": int(data.get("duration") or 0),
        "thumbnail": data.get("thumbnail"),
    }


def _clean_error(stderr: str) -> str:
    if not stderr:
        return ""
    line = stderr.strip().splitlines()[-1]
    return line.replace("ERROR: ", "")[:200]


def download(
    url: str,
    fmt: str,
    quality: str,
    out_dir: Path,
    job_id: str,
    on_progress: Optional[Callable[[int], None]] = None,
) -> Path:
    """Download via yt-dlp. Returns the path to the produced file."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "mp3":
        out_template = str(out_dir / f"{job_id}.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--no-warnings",
            "--newline",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", f"{quality}K" if quality.isdigit() else "192K",
            "-o", out_template,
            url,
        ]
        target = out_dir / f"{job_id}.mp3"
    else:
        # mp4
        if quality == "auto" or not quality.isdigit():
            fselector = "bv*+ba/b"
        else:
            fselector = f"bv*[height<={quality}]+ba/b[height<={quality}]"
        out_template = str(out_dir / f"{job_id}.%(ext)s")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--no-warnings",
            "--newline",
            "-f", fselector,
            "--merge-output-format", "mp4",
            "-o", out_template,
            url,
        ]
        target = out_dir / f"{job_id}.mp4"

    progress_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last_pct = 0
    assert proc.stdout is not None
    for line in proc.stdout:
        m = progress_re.search(line)
        if m and on_progress:
            try:
                pct = int(float(m.group(1)))
            except ValueError:
                pct = last_pct
            if pct != last_pct:
                last_pct = pct
                on_progress(pct)

    rc = proc.wait()
    if rc != 0:
        raise RuntimeError("Conversion failed")

    if not target.exists():
        # yt-dlp may pick a different container; find the file
        candidates = sorted(out_dir.glob(f"{job_id}.*"))
        if not candidates:
            raise RuntimeError("Output file not found")
        target = candidates[0]

    return target


def have_binaries() -> tuple[bool, str]:
    missing = [b for b in ("yt-dlp", "ffmpeg") if shutil.which(b) is None]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "ok"
