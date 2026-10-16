# ReturnGuard — one command per operation. Run from the app/ directory.

COMPOSE := docker compose
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help env up down logs ps migrate psql dev-api dev-worker dev-web \
        install test lint typecheck fmt check requirements clean

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

migrate: ## Apply database migrations
	$(COMPOSE) run --rm api alembic upgrade head

psql: ## Open a psql shell on the database
	$(COMPOSE) exec db psql -U returnguard -d returnguard

# --- Local development (outside Docker; needs `make up` for the db) ---
install: ## Install backend and frontend dependencies
	$(BACKEND) uv sync
	$(FRONTEND) npm ci

dev-api: ## Run the API with auto-reload
	$(BACKEND) LOG_JSON=false uv run uvicorn returnguard.main:app --reload --port 8000

dev-worker: ## Run the worker
	$(BACKEND) LOG_JSON=false uv run python -m returnguard.worker

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

requirements: ## Regenerate backend/requirements.txt from uv.lock
	$(BACKEND) uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt

clean: ## Stop the stack and delete the database volume
	$(COMPOSE) down -v
