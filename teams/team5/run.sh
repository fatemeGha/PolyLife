#!/usr/bin/env bash
# Team team5 — start (Linux/macOS/Git Bash).  Just run:  ./run.sh
# Creates .env from .env.example the first time, then starts the stack.
set -euo pipefail

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi
docker compose up --build
