#!/usr/bin/env bash
# Start ALL 8 team stacks (detached).  Run:  scripts/bash/start-all-teams.sh
# The core must already be running (start-core.sh) — it owns polylife_net.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"

for i in $(seq 1 8); do
    dir="$root/teams/team$i"
    [ -d "$dir" ] || { echo "team$i missing, skipping"; continue; }
    cd "$dir"
    [ -f .env ] || cp .env.example .env
    echo "==> starting team$i"
    docker compose up -d --build
done
echo "All teams started. Ports: team1=9101 ... team8=9108"
