# ReturnGuard — one command per operation. Run from the app/ directory.

COMPOSE := docker compose
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help env up down logs ps migrate seed embed-policy product-photos reset-db psql dev-prep dev-api dev-worker dev-web \
        install test lint typecheck fmt check api-types requirements clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

env: ## Create .env from .env.example (if missing)
	@test -f .env || (cp .env.example .env && echo "Created app/.env — fill in the keys")

# --- Docker stack ---
up: env ## Build and start db, api, worker, web
	$(COMPOSE) up -d --build --wait

down: ## Stop the stack (keeps the database volume)
	$(COMPOSE) down

logs: ## Follow logs for all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

seed: ## Load demo data (does nothing if users already exist)
	$(COMPOSE) run --rm -v ./seed:/srv/seed:ro -e SEED_DIR=/srv/seed api python -m returnguard.seed

embed-policy: ## Embed the active policy's clauses for Policy RAG (needs EMBEDDING_API_KEY; no-op without it)
	$(COMPOSE) run --rm api python -m returnguard.embed_policy

product-photos: ## Upload catalog photos from ../Photos to the product-photos bucket (only changes)
	$(BACKEND) LOG_JSON=false uv run python -m returnguard.product_photos ../../Photos

reset-db: ## Delete all data, then migrate and seed again (local or Neon)
	$(COMPOSE) run --rm api alembic downgrade base
	$(MAKE) migrate seed

migrate: ## Apply database migrations (to DATABASE_URL_UNPOOLED, or DATABASE_URL)
	$(COMPOSE) run --rm api alembic upgrade head

psql: ## Open a psql shell on the local Docker database
	$(COMPOSE) exec db psql -U returnguard -d returnguard

# --- Local development (outside Docker; needs `make up` for the db) ---
install: ## Install backend and frontend dependencies
	$(BACKEND) uv sync
	$(FRONTEND) npm ci

dev-prep: ## Stop the api, worker and web containers so the dev servers can take their ports
	$(COMPOSE) stop api worker web
	$(COMPOSE) up -d --wait db

dev-api: ## Run the API with auto-reload (wakes the dev worker on localhost:8001)
	$(BACKEND) LOG_JSON=false WORKER_WAKE_URL=http://localhost:8001/wake \
		uv run uvicorn returnguard.main:app --reload --port 8000 \
		--proxy-headers --forwarded-allow-ips 127.0.0.1

dev-worker: ## Run the worker (wake-ups on localhost:8001 only)
	$(BACKEND) LOG_JSON=false WORKER_WAKE_HOST=127.0.0.1 uv run python -m returnguard.worker

dev-web: ## Run the Next.js dev server
	$(FRONTEND) npm run dev

# --- Quality ---
test: ## Run backend tests (db tests need the stack up and migrated)
	$(BACKEND) uv run pytest

lint: ## Lint backend and frontend
	$(BACKEND) uv run ruff check . ../../tests && uv run ruff format --check . ../../tests
	$(FRONTEND) npm run lint

typecheck: ## Type-check backend and frontend
	$(BACKEND) uv run mypy src ../../tests
	$(FRONTEND) npm run typecheck

fmt: ## Auto-format backend code
	$(BACKEND) uv run ruff check --fix . ../../tests && uv run ruff format . ../../tests

check: lint typecheck test ## Everything CI runs

api-types: ## Regenerate openapi.json and the frontend's typed API client
	$(BACKEND) uv run python scripts/export_openapi.py ../frontend/openapi.json
	$(FRONTEND) npm run gen:api

requirements: ## Regenerate backend/requirements.txt from uv.lock
	$(BACKEND) uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt

clean: ## Stop the stack and delete the database volume
	$(COMPOSE) down -v
