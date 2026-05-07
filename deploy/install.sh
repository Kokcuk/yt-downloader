#!/usr/bin/env bash
# One-shot installer for a fresh Ubuntu 24.04 VPS.
# Run as root.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Kokcuk/yt-downloader.git}"
APP_DIR="${APP_DIR:-/opt/yt-saver}"

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg git ufw

if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing Docker"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "==> Configuring firewall"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Cloning / updating repo at $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" fetch --all --prune
    git -C "$APP_DIR" reset --hard origin/main
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Building and starting containers"
cd "$APP_DIR/deploy"
docker compose pull caddy
docker compose build backend
docker compose up -d

echo "==> Waiting for backend to report healthy"
for i in $(seq 1 30); do
    if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" 2>/dev/null; then
        echo "Backend healthy."
        break
    fi
    sleep 2
done

echo "==> Done. Containers:"
docker compose ps
