# Installing ReturnGuard locally

Everything runs on your machine with Docker. The only external services are the model
providers (Groq, OpenAI) and Langfuse Cloud, which are added in later milestones.

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Docker Desktop (with Compose v2) | 28+ | Running the stack |
| GNU Make | any | The commands below |
| uv | 0.9+ | Backend development and tests (optional for just running) |
| Node.js + npm | 24 + 11 | Frontend development (optional for just running) |

## Run the stack

All commands run from the `app/` directory.

```bash
cd app
make env        # creates app/.env from .env.example
make up         # builds and starts db, api, worker, web; waits until healthy
make migrate    # applies database migrations
```

Open <http://localhost:3000>. The **System status** panel should show **API ok** and
**Database ok**.

| Service | URL | What it is |
|---|---|---|
| web | <http://localhost:3000> | Next.js frontend (proxies `/api/*` to the API) |
| api | <http://localhost:8000/api/docs> | FastAPI, with interactive API docs |
| db | `localhost:5432` | Postgres 16 + pgvector (user / password / db: `returnguard`) |
| worker | — | Pipeline worker (logs only: `docker compose logs -f worker`) |

All ports are bound to `127.0.0.1` only.

Stop with `make down` (keeps data) or `make clean` (deletes the database volume).

## Develop

```bash
make install    # backend (uv sync) and frontend (npm ci) dependencies
make dev-api    # API with auto-reload on :8000   (needs the db from `make up`)
make dev-web    # Next.js dev server on :3000      (stop the `web` container first)
make check      # lint + type check + tests — the same as CI
```

Backend tests live in `/tests/backend`. Tests marked `db` need Postgres running and are
skipped locally when it isn't; CI runs them against a real Postgres and fails if it's missing.

Run `make help` for every command.

## Troubleshooting

- **`make up` hangs on "Waiting"** — check `docker compose logs api`; the API waits for
  the database health check.
- **Port already in use** — another service is on 3000, 5432, or 8000. Stop it or change the
  left-hand port in `docker-compose.yml`.
- **Database shows "unavailable"** — `docker compose ps` to check the `db` container; the
  API and worker recover on their own once it is back.
