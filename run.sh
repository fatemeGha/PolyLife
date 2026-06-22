#!/usr/bin/env bash
# PolyLife core — build & run with Docker (Linux / macOS / Git Bash).
# The React frontend is built automatically inside Docker; no local Node needed.
# After it starts, open http://localhost:8000
set -euo pipefail

docker compose up --build
