# Teams

Each of the 8 teams gets an identical, self-contained microservice template.
A team runs as its **own stack** (app + database + gateway) and authenticates
against the shared **core**.

```
teams/
  _template/      ← the canonical template (placeholders); do not run directly
  team1/ … team8/ ← generated per-team stacks (each on its own port + DB password)
```

## How a team fits in

```
browser ─▶ team gateway (nginx) ──auth_request──▶ core /api/verify
              │                                        │
              │        200 + X-User-*  ◀────────────────┘
              ▼
           team app  ──▶ team database (isolated, own password)
```

The gateway authenticates every `/api/` call against the core, so a team never
handles JWTs — it just trusts the `X-User-*` headers.

## Ports & DB passwords (dev only)

| Team  | URL                     | DB password        |
|-------|-------------------------|--------------------|
| team1 | http://localhost:9101   | `plf_team1_K7m2Qx` |
| team2 | http://localhost:9102   | `plf_team2_R3n8Vt` |
| team3 | http://localhost:9103   | `plf_team3_W9p4Lc` |
| team4 | http://localhost:9104   | `plf_team4_Z2h6Bn` |
| team5 | http://localhost:9105   | `plf_team5_D5k1Jr` |
| team6 | http://localhost:9106   | `plf_team6_F8s3Mq` |
| team7 | http://localhost:9107   | `plf_team7_T4v7Gx` |
| team8 | http://localhost:9108   | `plf_team8_Y6c9Pw` |

## Running a team

1. Start the core (repo root): `docker compose up`
2. Start a team: `cd teams/team1 && docker compose up --build`
3. Open the team URL above.

## Regenerating

Edit `teams/_template/`, then run `scripts/generate_teams.ps1` to rebuild all
eight team folders from the template.
