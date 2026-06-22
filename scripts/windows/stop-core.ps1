# Stop the PolyLife core (Windows).  Run:  scripts\windows\stop-core.ps1
# Stops & removes the core container. Named volumes (data) are kept.
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $root
try {
    docker compose down
} finally {
    Pop-Location
}
