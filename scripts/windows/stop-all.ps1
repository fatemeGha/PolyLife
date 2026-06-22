# Stop EVERYTHING — all 8 teams and the core (Windows).  Run:  scripts\windows\stop-all.ps1
# Stops & removes containers. Named volumes (data) are kept.
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")

foreach ($i in 1..8) {
    $dir = Join-Path $root "teams\team$i"
    if (-not (Test-Path $dir)) { continue }
    Push-Location $dir
    try {
        Write-Host "==> stopping team$i" -ForegroundColor Cyan
        docker compose down
    } finally {
        Pop-Location
    }
}

Push-Location $root
try {
    Write-Host "==> stopping core" -ForegroundColor Cyan
    docker compose down
} finally {
    Pop-Location
}
Write-Host "All services stopped." -ForegroundColor Green
