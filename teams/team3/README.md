# Team team3 — Roadmap

Your team's starting point. The stack already runs end-to-end with a
**placeholder** app; replace the placeholder with your real service step by step.

## Run it
1. Make sure the **core** is running first (repo root: `docker compose up`).
2. From this folder: `docker compose up --build`
3. Open **http://localhost:9103**

## What you get (already wired)
- **gateway** (nginx) — authenticates each `/api/` request against the core and
  injects `X-User-Id` / `X-User-Username`, then proxies to your app.
- **app** — placeholder on port 8000. **Replace `app/` with your code.**
- **db** — your own PostgreSQL, isolated from other teams:
  - database `team3` · user `team3_user` · password `plf_team3_W9p4Lc`

## Roadmap (suggested order)
- [ ] Replace `app/` with your stack (frontend + backend may live together).
- [ ] Read `X-User-Id` / `X-User-Username` from the request headers —
      **do not decode JWTs yourself**; the gateway + core already did.
- [ ] Connect to your database using the `DATABASE_URL` env var.
- [ ] Build your features. Keep serving on port **8000**.

> The password above is **dev-only**. Change it before any real deployment.
