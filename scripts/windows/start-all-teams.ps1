# Start ALL 8 team stacks (detached), Windows.  Run:  scripts\windows\start-all-teams.ps1
# The core must already be running (start-core.ps1) — it owns polylife_net.
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")

foreach ($i in 1..8) {
    $dir = Join-Path $root "teams\team$i"
    if (-not (Test-Path $dir)) { Write-Warning "team$i missing, skipping"; continue }
    Push-Location $dir
    try {
        if (-not (Test-Path .env)) { Copy-Item .env.example .env }
        Write-Host "==> starting team$i" -ForegroundColor Cyan
        docker compose up -d --build
    } finally {
        Pop-Location
    }
}
Write-Host "All teams started. Ports: team1=9101 ... team8=9108" -ForegroundColor Green
