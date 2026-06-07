#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required for local development."
  exit 1
fi

echo "==> AvatarFactory Docker-only dev setup"

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

echo "==> Building development containers"
docker compose -f docker-compose.dev.yml build

echo ""
echo "Setup complete."
echo "Next:"
echo "  make up"
echo "  make logs"
