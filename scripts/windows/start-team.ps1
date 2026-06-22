# Start a team's stack (Windows).  Example:  scripts\windows\start-team.ps1 1
# Creates the team's .env (from .env.example) the first time, then starts it.
param([Parameter(Mandatory = $true)][int]$Team)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dir = Join-Path $root "teams\team$Team"
if (-not (Test-Path $dir)) { throw "team$Team not found at $dir" }

Push-Location $dir
try {
    if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env" }
    docker compose up --build
} finally {
    Pop-Location
}
