$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not (Test-Path (Join-Path $RepoRoot ".env"))) {
    Copy-Item (Join-Path $RepoRoot ".env.example") (Join-Path $RepoRoot ".env")
}

docker compose --project-directory $RepoRoot -f (Join-Path $RepoRoot "docker-compose.yml") up --build -d
& (Join-Path $RepoRoot "scripts\windows\start-all-teams.ps1")
