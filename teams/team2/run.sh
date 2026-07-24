#!/usr/bin/env bash
#
# PolyLife Docker launcher for Team2.
#
# Usage:
#   ./teams/team2/run.sh team-up
#   ./teams/team2/run.sh all-up
#   ./teams/team2/run.sh all-down
#
# Running the script without an argument defaults to "team-up".

set -Eeuo pipefail

COMMAND="${1:-team-up}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEAM_COMPOSE="$SCRIPT_DIR/docker-compose.yml"
ROOT_ENV="$PROJECT_ROOT/.env"
NETWORK_NAME="polylife_net"

log() {
    printf '[PolyLife] %s\n' "$1"
}

fail() {
    printf '[PolyLife] ERROR: %s\n' "$1" >&2
    exit 1
}

find_compose_file() {
    local directory="$1"
    local candidate

    for candidate in \
        "$directory/docker-compose.yml" \
        "$directory/docker-compose.yaml" \
        "$directory/compose.yml" \
        "$directory/compose.yaml"; do
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

check_docker() {
    command -v docker >/dev/null 2>&1 ||
        fail "Docker is not installed or is not available in PATH."

    docker compose version >/dev/null 2>&1 ||
        fail "Docker Compose v2 is not available. Install Docker Desktop or the Compose plugin."
}

prepare_root_env() {
    local source_env=""

    if [[ -f "$ROOT_ENV" ]]; then
        return
    fi

    if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
        source_env="$PROJECT_ROOT/.env.example"
    elif [[ -f "$SCRIPT_DIR/.env.example" ]]; then
        source_env="$SCRIPT_DIR/.env.example"
    else
        fail "No .env or .env.example file was found in the project root or Team2 directory."
    fi

    cp "$source_env" "$ROOT_ENV"
    log "Created $ROOT_ENV from $source_env. Review its values before production use."
}

ensure_network() {
    if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
        log "Creating shared Docker network: $NETWORK_NAME"
        docker network create "$NETWORK_NAME" >/dev/null
    fi
}

compose_up() {
    local compose_file="$1"

    log "Starting: ${compose_file#"$PROJECT_ROOT"/}"
    docker compose \
        --env-file "$ROOT_ENV" \
        -f "$compose_file" \
        up -d --build
}

compose_down() {
    local compose_file="$1"

    log "Stopping: ${compose_file#"$PROJECT_ROOT"/}"
    docker compose \
        --env-file "$ROOT_ENV" \
        -f "$compose_file" \
        down --remove-orphans
}

collect_all_compose_files() {
    local root_compose
    local team_dir
    local team_compose

    root_compose="$(find_compose_file "$PROJECT_ROOT")" ||
        fail "The Core Compose file was not found in $PROJECT_ROOT."

    ALL_COMPOSE_FILES=("$root_compose")

    if [[ -d "$PROJECT_ROOT/teams" ]]; then
        for team_dir in "$PROJECT_ROOT"/teams/*; do
            [[ -d "$team_dir" ]] || continue

            if team_compose="$(find_compose_file "$team_dir")"; then
                ALL_COMPOSE_FILES+=("$team_compose")
            fi
        done
    fi
}

team_up() {
    [[ -f "$TEAM_COMPOSE" ]] ||
        fail "Team2 Compose file was not found: $TEAM_COMPOSE"

    prepare_root_env
    ensure_network
    compose_up "$TEAM_COMPOSE"

    log "Team2 services are running."
    log "Backend: http://localhost:8002/api/team2/health/"
    log "Gateway: http://localhost:9102/api/team2/health/"
}

all_up() {
    prepare_root_env
    ensure_network
    collect_all_compose_files

    local compose_file
    for compose_file in "${ALL_COMPOSE_FILES[@]}"; do
        compose_up "$compose_file"
    done

    log "Core and all team services are running."
}

all_down() {
    prepare_root_env
    collect_all_compose_files

    local index
    local failed=0

    # Stop team stacks first and Core last.
    for ((index = ${#ALL_COMPOSE_FILES[@]} - 1; index >= 0; index--)); do
        if ! compose_down "${ALL_COMPOSE_FILES[$index]}"; then
            failed=1
        fi
    done

    if ((failed != 0)); then
        fail "One or more Compose stacks could not be stopped. Check the Docker output above."
    fi

    log "All PolyLife services are stopped. Persistent volumes were preserved."
}

case "$COMMAND" in
    -h | --help | help)
        printf '%s\n' \
            "Usage: $0 {team-up|all-up|all-down}" \
            "  team-up   Build and start all Team2 services." \
            "  all-up    Build and start Core and every team Compose stack." \
            "  all-down  Stop Core and every team Compose stack (keeps volumes)."
        exit 0
        ;;
esac

check_docker

case "$COMMAND" in
    team-up)
        team_up
        ;;
    all-up)
        all_up
        ;;
    all-down)
        all_down
        ;;
    *)
        fail "Unknown command '$COMMAND'. Use team-up, all-up, or all-down."
        ;;
esac