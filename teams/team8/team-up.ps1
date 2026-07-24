$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created teams/team8/.env from .env.example"
}

# The assignment requires the shared network even when Core is not running.
docker network inspect polylife_net *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create polylife_net | Out-Null
    Write-Host "Created shared Docker network polylife_net"
}

docker compose up --build
