# Start the PolyLife core (Windows).  Run:  scripts\windows\start-core.ps1
# Builds the frontend + backend in Docker and serves on http://localhost:8000
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $root
try {
    docker compose up --build
} finally {
    Pop-Location
}
