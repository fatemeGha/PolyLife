# Team __TEAM__ — start (Windows).  Just run:  .\run.ps1
# Creates .env from .env.example the first time, then starts the stack.
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example"
}
docker compose up --build
