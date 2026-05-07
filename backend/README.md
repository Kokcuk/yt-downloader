# yt-saver backend

FastAPI service that wraps `yt-dlp` + `ffmpeg`. The frontend in `../frontend/` calls this.

## Run locally

Requires Python 3.11+, `ffmpeg`, and `yt-dlp` on PATH (or use Docker below).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/health`.

To wire up the frontend, copy `../frontend/config.example.js` to `../frontend/config.js` (set `YT_SAVER_API_BASE = "http://localhost:8000"`) and include it before `app.js`.

## Run with Docker

```bash
cd backend
docker build -t yt-saver .
docker run --rm -p 8000:8000 -v yt_saver_data:/data yt-saver
```

## Deploy

### Fly.io

```bash
cd backend
fly launch --no-deploy   # creates app, picks region; uses fly.toml
fly volumes create yt_saver_data --size 5 --region fra
fly deploy
```

### Cloudflare Containers (beta)

1. Install Wrangler v4+: `npm i -g wrangler`.
2. From the repo root create a `wrangler.toml` referencing this image and bind a Container.
3. `wrangler deploy`.

See https://developers.cloudflare.com/containers/ for the current binding/route syntax (it has changed during the beta).

### Hetzner / VPS

Build the image, push to your registry (or build on the box), then run with a systemd unit or `docker compose`. Example compose:

```yaml
services:
  yt-saver:
    image: yt-saver
    restart: unless-stopped
    ports: ["8000:8000"]
    volumes: ["yt_saver_data:/data"]
    environment:
      CORS_ORIGINS: "https://yoursite.example"
volumes:
  yt_saver_data:
```

Front it with Caddy or nginx for TLS.

## Environment variables

| Name | Default | Purpose |
|---|---|---|
| `FILES_DIR` | `/tmp/yt-saver` | Where converted files are written |
| `FILE_TTL_SECONDS` | `1800` | Files deleted this many seconds after completion |
| `MAX_DURATION_SECONDS` | `1800` | Reject videos longer than this |
| `MAX_CONCURRENT_JOBS` | `2` | Parallel yt-dlp processes |
| `RATE_LIMIT_PER_HOUR` | `10` | Requests/IP/hour for `/api/info` and `/api/jobs` |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins; set to your frontend domain in production |

## Endpoints

- `GET  /health` — binary check
- `GET  /api/info?url=<youtube>` — metadata
- `POST /api/jobs` `{url, format, quality}` → `{jobId}`
- `GET  /api/jobs/:id` — status / result
- `GET  /files/:id.<ext>` — converted file (deleted after TTL)
