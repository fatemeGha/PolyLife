# Team team5 — Workout Service

This folder contains the Django service for team 5. It runs behind the shared
gateway, reads the trusted `X-User-*` headers injected by the core, and serves
both HTML pages and REST APIs.

## Start
1. Make sure the **core** is running.
2. In this folder run `./run.sh` on macOS/Linux or `.
un.ps1` on Windows.
3. Open **http://localhost:9105**.

## Included
| File | Purpose |
|------|---------|
| `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `tests.py` | Django app code |
| `templates/team5/`, `static/team5/`, `migrations/` | app assets |
| `Dockerfile` | backend image |
| `docker-compose.yml` | gateway, backend, and database |
| `gateway.conf` | nginx gateway config |
| `.env.example` | local environment defaults |

## Notes
- The backend listens on port `8000` inside the compose network.
- Use `DATABASE_URL` from `.env` for the team database.
- Do not decode JWTs in this service; the gateway already authenticates the user.

