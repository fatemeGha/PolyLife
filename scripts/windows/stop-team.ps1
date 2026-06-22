# Stop a team's stack (Windows).  Example:  scripts\windows\stop-team.ps1 1
# Stops & removes the team's containers. Its database volume is kept.
param([Parameter(Mandatory = $true)][int]$Team)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$dir = Join-Path $root "teams\team$Team"
if (-not (Test-Path $dir)) { throw "team$Team not found at $dir" }

Push-Location $dir
try {
    docker compose down
} finally {
    Pop-Location
}
