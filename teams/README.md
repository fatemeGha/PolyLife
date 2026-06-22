# Teams

Each of the 8 teams is a **Django app** plus everything needed to run behind the
shared **gateway** and authenticate against the **core**.

```
teams/
  _template/      ← canonical template (placeholders); do not run directly
  team1/ … team8/ ← generated per-team workspaces (own port + DB password)
```

## How a team fits in

```
browser ─▶ team gateway (nginx) ──auth_request──▶ core /api/verify
              │                                        │
              │        200 + X-User-*  ◀────────────────┘
              ▼
           team backend  ──▶ team database (isolated, own password)
```

The gateway authenticates every `/api/` call against the core, so a team never
handles JWTs — it just trusts the `X-User-*` headers.

## Ports & DB passwords (dev only — secrets live in each team's `.env`)

| Team  | URL                   | DB password |
|-------|-----------------------|-------------|
| team1 | http://localhost:9101 | `team1pass` |
| team2 | http://localhost:9102 | `team2pass` |
| team3 | http://localhost:9103 | `team3pass` |
| team4 | http://localhost:9104 | `team4pass` |
| team5 | http://localhost:9105 | `team5pass` |
| team6 | http://localhost:9106 | `team6pass` |
| team7 | http://localhost:9107 | `team7pass` |
| team8 | http://localhost:9108 | `team8pass` |

Passwords are **not** in `docker-compose.yml` — they come from each team's
`.env` (created from `.env.example` by the run script). `.env` is git-ignored.

## Running

1. Start the core (repo root): `scripts\windows\start-core.ps1`.
2. Start a team: `scripts\windows\start-team.ps1 1`  — or `cd teams\team1 && .\run.ps1`.
3. Open the team URL above.

> `teams/_template/` is the reference each team folder was created from. Edit a
> team folder directly to work on that team.
