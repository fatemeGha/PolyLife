# Getting Started — for Students

You own **one team folder** (e.g. `teams/team3`). You barely touch Docker — one
script starts everything.

## First run (2 minutes)
1. Install **Docker Desktop** and make sure it's running.
2. Get the project and make sure the **core** is up. Usually your TA runs it; to
   run it yourself, from the repo root:
   ```
   scripts\windows\start-core.ps1     # Windows   (or)   scripts/bash/start-core.sh
   ```
   The core is now at http://localhost:8000 (sign up / log in there).
3. Start your team (say team3). From the repo root:
   ```
   scripts\windows\start-team.ps1 3     # Windows
   scripts/bash/start-team.sh 3         # mac/Linux
   ```
   …or `cd teams/team3` and run `.\run.ps1`.
4. Open your team URL, e.g. **http://localhost:9103**.

> The first time, the script copies `.env.example` → `.env` for you. Your DB
> password and port are already filled in there. You never edit `docker-compose.yml`.

## What you build
Your folder is a Django app. Work through `teams/teamX/README.md`:
- Build your backend (listening on port 8000) — `Dockerfile`.
- Uncomment `backend` + `db` in `docker-compose.yml`.
- In your code, read the user from the **headers** `X-User-Id` / `X-User-Username`
  (the gateway + core already authenticated them — **never decode JWTs**).
- Use `DATABASE_URL` (from `.env`) for your own database.
- Add models / views / urls / tests.

## Logging in (demo users)
The core comes seeded with simple users you can log in with:
`user1` / `user1pass`, `user2` / `user2pass`, `user3` / `user3pass`.

## Handy commands
- Stop your team:  `docker compose down`  (run inside your team folder)
- Rebuild after changes:  re-run the start script.
