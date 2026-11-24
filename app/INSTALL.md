# Installing ReturnGuard locally

Run the stack locally with Docker. Real inference uses a configured OpenAI-compatible
provider such as Groq. Neon and an embeddings provider are optional external services.
Langfuse is not integrated.

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

### Real inference with Groq

After `make env`, edit `app/.env` privately before starting the stack:

```dotenv
CHAT_API_KEY=<your Groq API key>
CHAT_BASE_URL=https://api.groq.com/openai/v1
CHAT_MODEL=<model enabled for your Groq account>
CHAT_EXTRA_BODY={}
```

Choose a model that supports JSON responses, function calling, streaming and image
inputs if demonstrating photo analysis. Provider-specific options in `.env.example` must match the chosen model.
Groq availability and rate limits depend on the account. Never paste keys into git,
screenshots or forum posts. After changing `.env`, run `docker compose up -d --force-recreate api worker`
from `app/` so both services reload it. A restart alone does not reload Compose env files.

`CHAT_TOOLS_ENABLED=true` enables the policy model's two read-only function tools.
`CHAT_STREAM_ENABLED=true` streams provider JSON for assembly before validation. These
are enabled by default. If a provider lacks either capability, disable that flag and
record the demo limitation. The reviewer Pipeline trace streams step metadata over SSE.

To record estimated dollar cost, set BOTH `CHAT_INPUT_USD_PER_MILLION` and
`CHAT_OUTPUT_USD_PER_MILLION` to the current prices for your configured model. Blank
values mean unknown, not free. Estimates are not billing statements.

Submit a synthetic return, open its reviewer trace and verify `source: model` plus model
usage in the step output. A deterministic window check can legitimately show `rules`.
Without `EMBEDDING_API_KEY`, the model receives the full policy. To use vector retrieval,
configure a separate embeddings provider returning 1536 dimensions, then `make embed-policy`.

An invalid configured key does not switch providers. Failures retry and eventually
escalate to a reviewer. See [demo runbook](../docs/demo.md) for the recovery demonstration.

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
works straight away. Click an order in **My orders** for its details (order ID, who
ordered it, placed and delivered times, shipping and billing addresses, the card's last 4
digits) and to return items from there.

Once a return is submitted, the worker reviews it (`docker compose logs -f worker`).
With `CHAT_API_KEY` configured, policy, photo analysis where needed, recommendation and
critic use real inference. With no key, conservative `RuleSteps` run instead. Automatic
approvals are off by default, so cases go to reviewers. A damage claim without a photo
returns "We need a photo"; uploading evidence queues another review.

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
make dev-prep   # stop the api, worker and web containers (keeps the local db for tests)
make dev-api    # API with auto-reload on :8000
make dev-worker # worker; restart it after changing pipeline code (it doesn't auto-reload)
make dev-web    # Next.js dev server with live reload on :3000
make check      # lint + type check + tests — the same as CI
make bias-audit # offline paired synthetic risk-group audit
make smoke      # read-only HTTP health/readiness/catalog check
```

Run each `dev-*` command in its own terminal. They use the same `app/.env` as Docker
(Neon and the photo bucket, if configured). `make up` switches back to the containers.

Backend tests live in `/tests/backend`. They use a separate `returnguard_test` database
(created and migrated automatically) and roll back every test, so they never touch your
demo data. Tests marked `db` need Postgres running and are skipped locally when it isn't;
CI runs them against a real Postgres and fails if it's missing.

### Product photos

Real catalog photos live in the Neon bucket `product-photos` (declared in `neon.ts`) and
are listed in the `product_photos` table. To add or change them, put the images in the
repo-root `Photos/` folder, one folder per product named after the product (or its SKU),
for example `Photos/shoes/Trailrunner Mesh Sneaker/img1.webp`, then run:

```bash
make product-photos
```

Images are used in filename order (the first is the main photo); JPEG, PNG, WebP and AVIF
all work. Each is re-encoded to a clean JPEG (at most 1200 px, no metadata). Re-running
uploads only changed photos and removes ones deleted from a folder; folders that don't
match a product are listed so you can rename them. `Photos/` is git-ignored: the photos
live in Neon, not in the repo.

Products without uploaded photos fall back to the generated illustrations in
`frontend/public/products/` (made by `seed/generate_product_images.py`).

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
