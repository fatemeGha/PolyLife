#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created teams/team8/.env from .env.example"
fi

# The assignment requires the shared network even when Core is not running.
docker network inspect polylife_net >/dev/null 2>&1 \
  || docker network create polylife_net >/dev/null

docker compose up --build
