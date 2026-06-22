#!/usr/bin/env bash
# Stop the PolyLife core.  Run:  scripts/bash/stop-core.sh
# Stops & removes the core container. Named volumes (data) are kept.
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose down
