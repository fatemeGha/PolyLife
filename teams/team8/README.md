# PolyLife — Team 8 / Microservice 3

This is my implementation of the internal fitness social network and learning management service for the Software Engineering project.

| Item | Value |
|---|---|
| Student | Amirhossein Bagheri |
| Student ID | 40031701 |
| Team | 8 — individual project |
| Topic | 3 — Social Network + LMS |
| Version | 1.1.0 |

## What is included

- A fitness social network with public profiles, real user posts, workout records, personal and explore feeds, follows, likes, threaded comments, post sharing, and reporting.
- One-to-one direct messages, read status, a working notification menu, and a detailed activity timeline.
- An educational content hub with categories, tags, articles, videos, draft/publish/archive states, filters, ratings, and recommendations.
- Free and paid courses with ordered lessons, server-side lesson access control, enrolment, lesson progress, a shopping cart, simulated checkout, and purchase history.
- Role-based training and diet plans.
- A standalone responsive React interface with RTL support, local Vazirmatn and Abril Fatface fonts, and the project colour palette.
- PostgreSQL, Redis, MinIO, Nginx forward authentication, a multi-stage Docker build, OpenAPI documentation, demo data, and CI checks.
- 62 automated service tests with 83% branch coverage, above the required 70%.

## Run with Docker

Docker Desktop with Compose v2 is required.

On Windows:

```powershell
cd teams/team8
.\all-up.ps1
```

On Linux or macOS:

```bash
cd teams/team8
chmod +x ./*.sh
./all-up.sh
```

Useful addresses:

- Application: <http://localhost:9108>
- Core login: <http://localhost:8000>
- Swagger UI: <http://localhost:9108/api/docs/>
- ReDoc: <http://localhost:9108/api/redoc/>
- Health check: <http://localhost:9108/health/>

`all-up` starts Core and all team stacks as required by the assignment. To run only Team 8, use `team-up.ps1` or `team-up.sh`. The Team 8 script also creates `polylife_net` when it does not exist. Authenticated endpoints still need Core to be running.

To stop everything:

```powershell
.\all-down.ps1
```

## Local development

The backend can also run without Docker:

```powershell
cd teams/team8
python -m venv .venv-team8
.\.venv-team8\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8008
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

In the normal Docker setup, Nginx asks Core to verify the cookie or bearer token and forwards the verified identity to the backend. The backend does not decode JWTs. If the API is run directly for development, a trusted local proxy must provide:

```text
X-User-Id: 1
X-User-Username: user1
X-Gateway-Secret: the GATEWAY_SHARED_SECRET value from .env
```

## Demo accounts

| ID | Username | Core password | Role | Main use |
|---:|---|---|---|---|
| 1 | user1 | `user1pass` | athlete | Feed, social actions, courses, and progress |
| 2 | user2 | `user2pass` | coach | Content, courses, and training plans |
| 3 | user3 | `user3pass` | nutrition_specialist | Nutrition content and diet plans |

`python manage.py seed_demo` is idempotent, so running it again does not duplicate the demo records.

## Tests and quality checks

```powershell
cd teams/team8
python manage.py check
python manage.py makemigrations --check --dry-run
coverage run --rcfile=.coveragerc manage.py test teams.team8.tests
coverage report --rcfile=.coveragerc
$openapiOutput = Join-Path $env:TEMP "team8-openapi.yaml"
python manage.py spectacular --file $openapiOutput --validate

cd frontend
npm ci
npm run lint
npm run build
```

The same checks, plus a Docker build, run in CI on pushes and pull requests.

## Documentation

The written submission documents are kept in the separate Team 8 delivery folder and are deliberately not versioned with the source repository. The running service still provides [Swagger](http://localhost:9108/api/docs/) and [ReDoc](http://localhost:9108/api/redoc/). The [Postman collection](postman/Team8.postman_collection.json) remains with the API source.

## Service layout

```text
Browser → Team 8 Nginx Gateway → Core /api/verify
                           └──→ Django REST API
                                  ├── PostgreSQL
                                  ├── Redis
                                  ├── MinIO
                                  └── Outbox events
```

Every Team 8 container joins the required shared `polylife_net` network and the private `team` network. Only the gateway has a public port. Since other team containers can also join the shared network, the backend accepts identity headers only when they include the matching `X-Gateway-Secret`.

## Environment variables

Copy `.env.example` to `.env`. The real `.env` file is ignored by Git.

- `URL_BASE_CORE`: internal Core address used by forward authentication.
- `URL_DATABASE`: connection string for the separate Team 8 PostgreSQL database.
- `CACHE_URL`: Redis connection string.
- `USE_S3` and `MINIO_*`: object-storage settings.
- `DJANGO_SECRET_KEY`: must be replaced with a secure random value outside development.
- `GATEWAY_SHARED_SECRET`: private value shared by the Team 8 gateway and backend.
- `TEAM_PORT`: public gateway port, which defaults to 9108.

## Security notes

- This service neither stores nor decodes passwords or JWTs.
- The backend has no public port and rejects untrusted identity headers.
- Image and video type and size limits are enforced.
- Owner, creator, coach, and nutrition permissions are checked by the API.
- Secrets stay outside the source tree and Docker Compose file.
- Domain records use soft deletion, while audit and outbox records remain available.
