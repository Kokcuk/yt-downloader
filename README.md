# yt-downloader

Static frontend + FastAPI/yt-dlp backend.

```
docs/        Specs (idea.md, frontend-spec.md)
frontend/    Static site — Bootstrap 2.0.2, deploy to any static host (Cloudflare Pages, Netlify, GitHub Pages)
backend/     FastAPI + yt-dlp + ffmpeg in Docker — see backend/README.md for deploy options
```

## Local dev

In one terminal:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In another terminal serve the frontend:

```bash
cd frontend
cp config.example.js config.js   # already points at http://localhost:8000
python -m http.server 5173
```

Open http://localhost:5173. (Add `<script src="config.js"></script>` before `app.js` in `index.html` if you create `config.js`; otherwise the frontend assumes same-origin.)
