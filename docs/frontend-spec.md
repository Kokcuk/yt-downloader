# Frontend Spec — YouTube Downloader

## 1. Overview

A single-page, frontend-only YouTube downloader. The user pastes a YouTube URL, selects a quality, and clicks one of two buttons to download the video (MP4) or audio (MP3). Visual style is intentionally retro/minimal, based on the Bootstrap 2.0.2 "Hero" example.

References for layout and copy tone:
- https://getbootstrap.com/2.0.2/examples/hero.html (visual baseline)
- https://v18.www-y2mate.com/ (input + action layout)
- https://app.ytdown.to/en27/ (input + SEO copy block)

## 2. Goals & Non-Goals

**Goals**
- One screen, one job: paste URL → pick quality → download.
- Static frontend (Bootstrap 2.0.2) talking to our own thin backend that wraps `yt-dlp` (see §7).
- Recognizable, lightweight UI using Bootstrap 2.0.2.
- SEO copy below the input to support search ranking.

**Non-Goals**
- No accounts, no history, no playlists, no batch downloads.
- No server-side video processing on our infrastructure.
- No mobile app.

## 3. Tech Stack

- **HTML5** + **Bootstrap 2.0.2** (CSS + JS via CDN).
- **jQuery 1.7.x** (required by Bootstrap 2.0.2 plugins).
- **Vanilla JS** for app logic. No build step.
- Single `index.html`, optional `app.js` and `styles.css`.
- Hosted as static files (GitHub Pages, Netlify, Cloudflare Pages, etc.).

CDN snippets:
```
https://cdn.jsdelivr.net/npm/bootstrap@2.0.2/docs/assets/css/bootstrap.css
https://cdn.jsdelivr.net/npm/bootstrap@2.0.2/docs/assets/js/bootstrap.js
```

## 4. Page Structure

Single page, top-to-bottom:

1. **Navbar** (Bootstrap `.navbar .navbar-fixed-top`) — site name on the left, anchor links (Home, FAQ, Contact) on the right.
2. **Hero unit** (`.hero-unit`) — H1 title, short tagline.
3. **Downloader form** (centered, max-width ~720px) — URL input, quality select, two action buttons.
4. **SEO description block** — 3–4 sentences directly under the form.
5. **"How it works"** — three columns (`.row` with three `.span4`), one short step each.
6. **FAQ** — 4–6 collapsible items (Bootstrap `collapse` plugin).
7. **Footer** — copyright, links to Terms / Privacy / DMCA.

## 5. Components

### 5.1 URL Input
- `<input type="url" class="input-xxlarge" placeholder="Paste YouTube link here…">`.
- Full width of the form container on small screens.
- Trim whitespace on input/blur.
- Visible validation state (`.control-group.error` / `.success`) updated on change.

### 5.2 Quality Selector
- `<select class="input-medium">` with options:
  - `Auto (best)` — default
  - `1080p`, `720p`, `480p`, `360p`, `240p`, `144p` (video)
  - For MP3 the selector is hidden or replaced with bitrate (`128 kbps`, `192 kbps`, `320 kbps`); see §6.
- Inline next to the buttons on desktop, stacked on mobile.

### 5.3 Action Buttons
- **Download MP4** — `<button class="btn btn-primary btn-large">`.
- **Download MP3** — `<button class="btn btn-large">` (secondary styling).
- Disabled until URL passes regex validation (§6.1).
- While a request is in flight, button text becomes `Processing…` and the button is disabled. The other button is also disabled to prevent double-submits.

### 5.4 Result Card
- Hidden by default. Rendered after a successful API response.
- Contents:
  - Video thumbnail (left, ~120px wide).
  - Title (H4), duration, channel name.
  - "Download" anchor (`<a class="btn btn-success" download>`) pointing at the resolved file URL.
- Includes a "Download another" link that resets the form.

### 5.5 Error Alert
- Bootstrap `.alert .alert-error`, dismissible.
- Shown for: invalid URL, video not found, API error, network error.
- Copy is plain English, no stack traces.

### 5.6 SEO Block
- Plain `<p>` under the form, styled with `.muted`.
- 3–4 sentences. Example draft:

> Download YouTube videos as MP4 or extract audio as MP3 in seconds. Paste any YouTube link, choose your preferred quality, and save the file directly to your device. Our converter is free, requires no signup, and works on desktop and mobile browsers. Use it for personal, offline viewing of content you have the right to download.

## 6. Behavior

### 6.1 URL Validation
Accept canonical YouTube URL forms:
- `https://www.youtube.com/watch?v=<id>`
- `https://youtu.be/<id>`
- `https://www.youtube.com/shorts/<id>`
- `https://m.youtube.com/watch?v=<id>`

Regex (illustrative):
```
/^(https?:\/\/)?(www\.|m\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)([\w-]{11}).*/
```

On invalid: show inline error under the input, keep buttons disabled.

### 6.2 Submit Flow
1. User clicks MP4 or MP3.
2. Frontend extracts the 11-char video id.
3. Calls the conversion API with `{ id, format, quality }`.
4. Polls the API until status is `ready` (or fails after a timeout, default 60s).
5. Renders the Result Card with the download link.

### 6.3 Loading & Progress
- Show a Bootstrap `.progress .progress-striped .active` bar during processing.
- If the API reports percent progress, reflect it; otherwise indeterminate.

### 6.4 Quality Behavior
- For MP4: send selected resolution; if unavailable, API returns the closest lower resolution and we show a `.alert-info` note ("1080p unavailable — serving 720p").
- For MP3: bitrate values map to `audio_bitrate` in the API request.

## 7. Backend — Self-Hosted yt-dlp

YouTube blocks direct browser downloads. Rather than depend on a third-party converter, we run our own thin backend wrapping [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

### 7.1 Why self-hosted

- No per-call cost or rate caps from a vendor.
- Doesn't break when a RapidAPI provider disappears — `yt-dlp` is actively maintained.
- Full control over supported formats, quality ladder, and headers.
- Trade-off accepted: we now own a small server. The frontend is still static; only the conversion endpoint is dynamic.

### 7.2 Stack

- **Runtime:** Python 3.11+ with **FastAPI** (or Node + `youtube-dl-exec`; FastAPI assumed below for concreteness).
- **Worker:** `yt-dlp` invoked as a subprocess, plus `ffmpeg` for MP3 extraction and MP4 muxing.
- **Container:** single Docker image (`python:3.11-slim` + `ffmpeg` + `yt-dlp`).
- **Hosting candidates:** Fly.io, Railway, Hetzner Cloud, or a small VPS. **Avoid** large shared cloud egress IPs (AWS/GCP/Azure) — YouTube frequently 429s/blocks them. Hosting target is deferred (see Open Questions).

### 7.3 HTTP API

The frontend talks only to our backend. CORS is restricted to our own origin.

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/info?url=<youtube-url>` | Metadata: title, thumbnail, duration, available formats |
| `POST` | `/api/jobs` body `{url, format, quality}` | Create a conversion job, returns `{jobId}` |
| `GET`  | `/api/jobs/:id` | Job status: `queued` \| `processing` \| `ready` \| `error`, plus `progress` (0–100) and `downloadUrl` when ready |
| `GET`  | `/files/:id.<ext>` | Streams the converted file with `Content-Disposition: attachment` |

Job records live in memory (or Redis if we scale beyond one node). Files are written to a temp directory and deleted after first successful download or after a TTL (default 30 minutes), whichever comes first.

### 7.4 Conversion logic

- **MP4:** `yt-dlp -f "bv*[height<=Q]+ba/b[height<=Q]" --merge-output-format mp4` where `Q` is the requested resolution. `Auto (best)` drops the height constraint.
- **MP3:** `yt-dlp -x --audio-format mp3 --audio-quality <bitrate>` (e.g. `192K`).
- If the requested quality isn't available, yt-dlp picks the closest lower; the API surfaces the actual height/bitrate in the job result so the UI can show the "1080p unavailable — serving 720p" notice (§6.4).

### 7.5 Abuse & cost controls

- Per-IP rate limit (e.g. 10 jobs/hour) enforced in middleware.
- Max video duration (e.g. 30 minutes) checked against `/info` before queuing.
- Concurrency cap on the worker (e.g. 2 simultaneous yt-dlp processes) to keep CPU/egress predictable.
- Optional Cloudflare in front of the host for DDoS protection and bot challenges.

### 7.6 Frontend integration

The frontend's API client is a single module exposing `fetchInfo(url)`, `createJob(url, format, quality)`, and `pollJob(id)`. Swapping providers later (back to RapidAPI, or a different self-hosted tool) means rewriting only this module.

## 8. Layout & Styling

- 12-column Bootstrap grid; main form lives in `.row > .span8.offset2`.
- Mobile-first: form stacks vertically below 768px (Bootstrap 2.0.2 has limited responsive helpers — load `bootstrap-responsive.css`).
- Color: stay close to Bootstrap 2.0.2 defaults (off-white background, dark navbar). One brand accent color on the primary button.
- Custom CSS lives in `styles.css` and only overrides what's necessary (hero spacing, form alignment, result card layout).

## 9. Accessibility

- All inputs have associated `<label>` elements (visually hidden where the placeholder is sufficient).
- Buttons reachable by keyboard; focus states preserved (do not strip outlines).
- Error alerts use `role="alert"` so screen readers announce them.
- Color contrast checked against WCAG AA for body text and primary button.

## 10. SEO

- `<title>`: "Free YouTube to MP4 & MP3 Downloader — <SiteName>".
- Meta description (~155 chars) mirroring the on-page SEO block.
- Open Graph + Twitter Card tags.
- One `<h1>` (hero), descriptive `<h2>` per section.
- JSON-LD `WebApplication` schema.
- Sitemap.xml + robots.txt.

## 11. Analytics

**Google Analytics 4** — measurement ID `G-MP2RGFWQGH`.

Snippet placed in `<head>` of `index.html`:

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-MP2RGFWQGH"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-MP2RGFWQGH');
</script>
```

Custom events (sent with `gtag('event', ...)`):
- `download_click_mp4` — fired when the MP4 button is clicked (params: `quality`).
- `download_click_mp3` — fired when the MP3 button is clicked (params: `bitrate`).
- `download_success` — fired when the user receives a `ready` job result (params: `format`, `quality`, `duration_s`).
- `download_error` — fired on API/validation failure (params: `reason`).

No PII is sent. The submitted YouTube URL is never logged as an event parameter.

## 12. Legal Footer

- Disclaimer that users must own rights / have permission for content they download.
- Links: Terms, Privacy, DMCA / takedown contact.
- Not legal advice — confirm with counsel before launch.

## 13. File Layout

```
/
├── index.html
├── app.js
├── styles.css
└── assets/
    ├── logo.svg
    └── favicon.ico
```

## 14. Open Questions

1. Domain name and hosting target — deferred, decide later.

## 15. Decisions

- **Conversion backend**: self-hosted `yt-dlp` behind a thin FastAPI service in Docker. No third-party API dependency. Frontend talks only to our own `/api/*` endpoints (same origin, no API keys in the browser).
- **Localization**: English only at launch. No i18n framework, no translation files.