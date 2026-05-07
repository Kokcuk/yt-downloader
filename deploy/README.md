# Deploy

Single-VPS deploy: Caddy (TLS + static frontend + reverse proxy) + backend container.

## Layout

```
deploy/
├── docker-compose.yml   # backend + caddy
├── Caddyfile            # auto-TLS for youtube-downloader.org
└── install.sh           # one-shot bootstrap for fresh Ubuntu 24.04
```

## First deploy on a fresh VPS

DNS for `youtube-downloader.org` and `www.youtube-downloader.org` must point at the VPS **before** running this (so Caddy can complete the ACME HTTP-01 challenge). Use **DNS-only** (gray cloud) in Cloudflare for the first cert; you can switch to **Proxied** (orange cloud) afterwards.

```bash
ssh root@<vps-ip>
curl -fsSL https://raw.githubusercontent.com/Kokcuk/yt-downloader/main/deploy/install.sh | bash
```

## Update an existing deploy

```bash
ssh root@<vps-ip>
cd /opt/yt-saver
git pull
cd deploy
docker compose build backend
docker compose up -d
```

## Logs

```bash
docker compose -f /opt/yt-saver/deploy/docker-compose.yml logs -f --tail=200
```

## Notes

- The backend listens on port 8000 inside the Docker network only — Caddy is the only thing exposed to 80/443.
- Converted files live in the `yt_data` Docker volume and self-delete after `FILE_TTL_SECONDS` (default 30 min).
- To change settings, edit env values in `docker-compose.yml` and `docker compose up -d` again.
