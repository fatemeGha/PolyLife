# Team team7 — Roadmap

Your team's workspace. It's a Django app skeleton plus everything needed to run
behind the shared gateway. Build it up step by step.

## Start (you barely touch Docker)
1. Make sure the **core** is running (ask your TA, or run `scripts/windows/start-core.ps1`).
2. In this folder run:  **`.\run.ps1`**  (Windows) or **`./run.sh`** (mac/Linux)
   - it creates `.env` from `.env.example` and starts your stack.
3. Open **http://localhost:9107**

> Out of the box only the **gateway** runs, so app routes return `502` until you
> add your backend — that's expected. Your first job is to build the service.

## What's here
| File | What it is |
|------|------------|
| `models.py` `views.py` `urls.py` `admin.py` `tests.py` | your Django app |
| `migrations/` `static/team7/` `templates/team7/` | app folders |
| `Dockerfile` | how your backend is built (replace with your stack) |
| `docker-compose.yml` | gateway (+ commented backend/db you enable) |
| `gateway.conf` | authenticates `/api/` against the core, then proxies to you |
| `.env.example` | your port, DB credentials, secret — **secrets live here, not in compose** |

## Roadmap (suggested order)
- [ ] Build your backend so it listens on port **8000** (`Dockerfile`).
- [ ] Uncomment `backend` and `db` in `docker-compose.yml`.
- [ ] Read `X-User-Id` / `X-User-Username` from request headers — the gateway +
      core already authenticated the user; **never decode JWTs yourself**.
- [ ] Use `DATABASE_URL` (from `.env`) for your own database.
- [ ] Add models, views, urls, and tests. Build your features.

> The password in `.env.example` is **dev-only**. Change it for any real use.
