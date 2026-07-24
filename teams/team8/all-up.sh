#!/usr/bin/env bash
set -euo pipefail
TEAM_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$TEAM_DIR/../.." && pwd)"

[ -f "$REPO_ROOT/.env" ] || cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"

docker compose --project-directory "$REPO_ROOT" -f "$REPO_ROOT/docker-compose.yml" up --build -d
"$REPO_ROOT/scripts/bash/start-all-teams.sh"
