#!/usr/bin/env bash
# Stop EVERYTHING — all 8 teams and the core.  Run:  scripts/bash/stop-all.sh
# Stops & removes containers. Named volumes (data) are kept.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"

for i in $(seq 1 8); do
    dir="$root/teams/team$i"
    [ -d "$dir" ] || continue
    cd "$dir"
    echo "==> stopping team$i"
    docker compose down
done

cd "$root"
echo "==> stopping core"
docker compose down
echo "All services stopped."
