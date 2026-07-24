# PolyLife — Core

Software Engineering 1 course project — 1404/1405.

This repository is the **core** of PolyLife: a Django project that provides the
shared infrastructure (authentication, the landing/home page, and the auth
gateway for the team microservices). Each student team builds its own service —
with its **own database** and **own gateway** — behind this core.

## Architecture

```
 browser ───────────────▶ Core (Django)               http://localhost:8000
                           • React landing page (SPA)
                           • /api/register | login | user
                           • /api/verify  (forward-auth for teams)
                                  ▲
 browser ─▶ team gateway (nginx) ─┘  http://localhost:910N
              │
              ▼
           team backend ──▶ team's own database (with a unique password)
```

- **Auth:** username + password → JWT. The core verifies the token; teams never
  decode JWTs — their gateway calls `/api/verify` and forwards the `X-User-*`
  headers to the backend.

  ## Suggested flow

1. **Register** — `POST /api/register` with `{"username": "ali", "password": "Sup3rSecretPass"}`.
2. **Login** — `POST /api/login` with the same credentials. The response returns
   `token`/`refresh` and sets an HttpOnly access cookie so browser sessions also
   work through team gateways on ports `9101`…`9108`.
3. **Get user** — `GET /api/user` with `Authorization: Bearer <token>`.
4. **Refresh** — `POST /api/refresh` with `{"refresh": "<refresh>"}` → a fresh `token`.
5. **Verify** — `GET /api/verify` with the Bearer token → check the `X-User-*` response headers (this is what a team gateway calls).
6. **Logout** — `POST /api/logout` with the Bearer token. Afterwards the same token/refresh stop working.


- **Isolation:** each team has its own database with its own user/password.

## Layout

| Path | Description |
|------|-------------|
| `polylife/` | Django project (settings, urls, per-team DB router) |
| `core/` | core app: User model, JWT, auth API, middleware, `verify` |
| `frontend/` | React/Vite landing page (built inside Docker) |
| `teams/` | the 8 team templates — student guide: `teams/GETTING_STARTED.md` |
| `scripts/` | helper scripts to start/stop the core and teams (`windows/`, `bash/`) |

## Run (with Docker — recommended)

```powershell
scripts\windows\start-core.ps1        # core      → http://localhost:8000
scripts\windows\start-team.ps1 1      # one team  → http://localhost:9101
scripts\windows\start-all-teams.ps1   # all 8 teams (9101..9108)
```
Stop: `scripts\windows\stop-core.ps1` , `scripts\windows\stop-team.ps1 1` , `scripts\windows\stop-all.ps1` (everything).
Bash equivalents live in `scripts/bash/*.sh`.

Seeded demo users: `user1/user1pass` , `user2/user2pass` , `user3/user3pass`.

## Run the core without Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```
(The React page only renders when built in Docker; locally you get a fallback
page plus the fully working API.)

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py test core
```

To exercise the API by hand (Postman / curl), see [docs/API_TESTING.md](docs/API_TESTING.md).

## Configuration

For local settings, copy `.env.example` to `.env`. No secret is ever committed.
