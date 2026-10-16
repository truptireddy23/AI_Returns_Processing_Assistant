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
make seed       # loads the demo data (safe to re-run; does nothing if already loaded)
```

Open <http://localhost:3000>. The **System status** panel should show **API ok** and
**Database ok**. Then **Sign in** with one of the demo accounts.

### Demo accounts

The seed creates 7 customers, 2 reviewers, and 1 admin. Emails and the shared demo
password for each role are in [`seed/users.json`](seed/users.json) (local development
only; the seed refuses to run when `ENVIRONMENT=production`).

| Role | Example account | Lands on |
|---|---|---|
| Customer | `jordan.ellis@example.com` | My orders |
| Reviewer | `riley.chen@example.com` | Review queue |
| Admin | `priya.shah@example.com` | Automation settings |

Each customer is set up for a demo case (clean history, high return rate, two accounts
sharing an address, a brand-new account); see `seed/users.json` and
`seed/demo_orders.json`. Order dates are relative to when you seed, so re-seed with
`make reset-db` if the demo orders drift outside the return window.

| Service | URL | What it is |
|---|---|---|
| web | <http://localhost:3000> | Next.js frontend (proxies `/api/*` to the API) |
| api | <http://localhost:8000/api/docs> | FastAPI, with interactive API docs |
| db | `localhost:5432` | Postgres 16 + pgvector (user / password / db: `returnguard`) |
| worker | — | Pipeline worker (logs only: `docker compose logs -f worker`) |

All ports are bound to `127.0.0.1` only.

Stop with `make down` (keeps data), `make reset-db` (wipes and re-seeds the data), or
`make clean` (deletes the database volume).

## Develop

```bash
make install    # backend (uv sync) and frontend (npm ci) dependencies
make dev-api    # API with auto-reload on :8000   (needs the db from `make up`)
make dev-web    # Next.js dev server on :3000      (stop the `web` container first)
make check      # lint + type check + tests — the same as CI
```

Backend tests live in `/tests/backend`. They use a separate `returnguard_test` database
(created and migrated automatically) and roll back every test, so they never touch your
demo data. Tests marked `db` need Postgres running and are skipped locally when it isn't;
CI runs them against a real Postgres and fails if it's missing.

After changing an API endpoint, run `make api-types` to regenerate `frontend/openapi.json`
and the typed client in `frontend/src/lib/api-schema.d.ts`; CI fails if they're stale.

Run `make help` for every command.

## Troubleshooting

- **`make up` hangs on "Waiting"** — check `docker compose logs api`; the API waits for
  the database health check.
- **Port already in use** — another service is on 3000, 5432, or 8000. Stop it or change the
  left-hand port in `docker-compose.yml`.
- **"Too many attempts" when signing in** — sign-in is rate limited per address and per
  account (counters are in memory); `docker compose restart api` clears them locally.
- **Database shows "unavailable"** — `docker compose ps` to check the `db` container; the
  API and worker recover on their own once it is back.
