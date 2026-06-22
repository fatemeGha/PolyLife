#!/usr/bin/env bash
# Stop a team's stack.  Example:  scripts/bash/stop-team.sh 1
# Stops & removes the team's containers. Its database volume is kept.
set -euo pipefail
team="${1:?usage: stop-team.sh <team-number>}"
cd "$(dirname "$0")/../../teams/team${team}"
docker compose down
