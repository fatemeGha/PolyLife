#!/usr/bin/env bash
# Start a team's stack.  Example:  scripts/bash/start-team.sh 1
set -euo pipefail
team="${1:?usage: start-team.sh <team-number>}"
cd "$(dirname "$0")/../../teams/team${team}"
[ -f .env ] || { cp .env.example .env; echo "Created .env"; }
docker compose up --build
