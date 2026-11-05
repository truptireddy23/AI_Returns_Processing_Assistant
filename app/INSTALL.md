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

## Choose a database

The app runs on either database; `DATABASE_URL` in `app/.env` decides.

| | Hosted: **Neon** (shared demo data) | Local: Docker Postgres |
|---|---|---|
| Use it for | The team's shared data and the live demo | Working offline, or a private copy |
| Set up | See [Connect to Neon](#connect-to-neon) | Leave `DATABASE_URL` and `DATABASE_URL_UNPOOLED` empty |

Tests always use their own local database (`returnguard_test`), whichever you choose, so
`make up` still starts the local Postgres container.

### Connect to Neon

The project is `returnguard` (`patient-cake-09777018`), branch `production`, in
`aws-us-east-2`. Ask Aditya to invite you to the Neon organization, then:

```bash
npm i -g neon               # Neon CLI
neon login                  # finish signing in in the browser
neon link --project-id patient-cake-09777018 --branch production -y   # from the repo root
neon env pull --file app/.env
```

That writes two connection strings into `app/.env`; paste them as-is, the app adapts
them for its driver:

- `DATABASE_URL` — pooled (`-pooler` in the host). The app and worker use it.
- `DATABASE_URL_UNPOOLED` — direct. `make migrate` uses it, because migrations must
  not go through a transaction pooler.

Neon scales to zero after a few idle minutes: the first request afterwards takes a
moment longer while it wakes. The worker deliberately doesn't query the database while
it's idle, so the database can sleep and stay within the free plan's compute hours.

`neon.ts` (repo root) declares the Neon services this project uses: Postgres and a
private Object Storage bucket, `return-photos`, for the photos customers upload with a
return. `neon deploy` applies it. The same `neon env pull --file app/.env` also writes the
bucket's `AWS_*` credentials; without them, photos are kept in `app/storage/` on your
machine instead (fine offline, but other people won't see them).

## Run the stack

All commands run from the `app/` directory.

```bash
cd app
make env        # creates app/.env from .env.example
make up         # builds and starts db, api, worker, web; waits until healthy
make migrate    # applies database migrations
make seed       # loads the demo data (safe to re-run; does nothing if already loaded)
```

On Neon, `migrate` and `seed` only need running once for the whole team; they're already
done for the `production` branch.

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

Anyone can also **Create account** (customers only; staff accounts come from the seed).
Passwords need at least 10 characters and can't be your email or a common password.

Customers can browse the **Shop**, add to the **Cart**, and check out with the test card
`4242 4242 4242 4242` (any future expiry, any 3-digit code; no money moves, and only test
card numbers are accepted). Delivery is instant in the demo, so **My orders → Return item**
works straight away.

Once a return is submitted, the **worker** reviews it within a few seconds (the API wakes
it directly; `docker compose logs -f worker` shows each step). Until the AI steps arrive
(M5/M6), the policy, photo, recommendation, and critic steps are rule-based stand-ins:
returns that need a photo always go to a person as "unverified photo", and with
automatic approvals off (the default) every case goes to a person. A damage claim without
a photo comes back to the customer as "We need a photo", and adding it from the return's
page starts the review again.

Each customer is set up for a demo case (clean history, high return rate, two accounts
sharing an address, a brand-new account); see `seed/users.json` and
`seed/demo_orders.json`. Order dates are relative to when you seed, so re-seed with
`make reset-db` if the demo orders drift outside the return window.

| Service | URL | What it is |
|---|---|---|
| web | <http://localhost:3000> | Next.js frontend (proxies `/api/*` to the API) |
| api | <http://localhost:8000/api/docs> | FastAPI, with interactive API docs |
| db | `localhost:5432` | Local Postgres 16 + pgvector (user / password / db: `returnguard`); used by tests, and by the app when `DATABASE_URL` is empty |
| worker | — | Pipeline worker (logs only: `docker compose logs -f worker`) |

All ports are bound to `127.0.0.1` only.

Stop with `make down` (keeps data). `make reset-db` wipes and re-seeds whichever database
`DATABASE_URL` points at, **including Neon, for everyone**, so check before running it.
`make clean` deletes the local database volume.

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

Product images live in `frontend/public/products/` and are generated by
`seed/generate_product_images.py` (run it from `backend/` with `uv run python
../seed/generate_product_images.py` after adding products).

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
- **`Migrations need a direct connection`** — set `DATABASE_URL_UNPOOLED` (run
  `neon env pull --file app/.env` again).
- **First request is slow / times out once** — Neon was asleep; retry.
- **A return stays "Submitted"** — check `docker compose logs worker`. The API wakes the
  worker over the internal network; if that wake-up is lost, the worker's backstop sweep
  (every 30 minutes) still picks the job up, or restart the worker to look immediately.
- **Database shows "unavailable"** — `docker compose ps` to check the `db` container; the
  API and worker recover on their own once it is back.
