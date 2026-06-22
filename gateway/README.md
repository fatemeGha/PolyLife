# Team API Gateway

Every team microservice sits behind its own **nginx gateway**. The gateway is
the single entry point for a team and does three things:

1. Serves the team's **frontend** (`/`).
2. Proxies the team's **API** (`/api/`) to the team **backend**.
3. **Authenticates** every API request against the PolyLife **core** before it
   reaches the backend — using nginx `auth_request` (forward-auth).

## How forward-auth works

```
 client ──▶ gateway ──auth_request──▶ core  /api/verify
                          │                     │
                          │   200 + X-User-*  ◀──┘  (valid JWT)
                          ▼
                       backend  (receives X-User-Id / X-User-Username)
```

- The gateway sends a subrequest to the core's `GET /api/verify`, forwarding the
  caller's `Authorization` / `Cookie`.
- `200` → the core also returns `X-User-Id` and `X-User-Username`; the gateway
  injects them as headers into the proxied request, so the team backend trusts
  the gateway and never parses tokens itself.
- `401` → the request is rejected (here, redirected to the core login page).

## Using it

`gateway.conf` is the reusable template. A team's `docker-compose.yml` mounts it
into an `nginx:alpine` container and joins the shared `polylife_net` network so
`core`, `frontend`, and `backend` resolve by name. A full, runnable team stack
that wires this up is generated in the team template (next step).
