.PHONY: help setup docker-up docker-down docker-config \
	web-dev admin-dev api-dev \
	lint typecheck test \
	lint-web lint-admin lint-api \
	typecheck-web typecheck-admin typecheck-api \
	test-web test-admin test-api test-mobile \
	analyze-mobile format format-check \
	db-upgrade db-downgrade db-history db-current db-revision

help:
	@echo "Common targets: setup, docker-up, docker-down, lint, typecheck, test"

## --- Setup ---
setup:
	npm install
	cd apps/api && python -m venv .venv
	cd apps/api && .venv/Scripts/python -m pip install -e ".[dev]"
	cd apps/mobile && flutter pub get

## --- Docker (Postgres + Redis + API) ---
docker-up:
	docker compose up -d postgres redis

docker-down:
	docker compose down

docker-config:
	docker compose config

## --- Dev servers ---
web-dev:
	npm run dev --workspace=apps/web

admin-dev:
	npm run dev --workspace=apps/admin

api-dev:
	cd apps/api && .venv/Scripts/uvicorn app.main:app --reload

## --- Lint ---
lint: lint-web lint-admin lint-api

lint-web:
	npm run lint --workspace=apps/web

lint-admin:
	npm run lint --workspace=apps/admin

lint-api:
	cd apps/api && .venv/Scripts/python -m ruff check .

## --- Type checking ---
typecheck: typecheck-web typecheck-admin typecheck-api

typecheck-web:
	npm run typecheck --workspace=apps/web

typecheck-admin:
	npm run typecheck --workspace=apps/admin

typecheck-api:
	cd apps/api && .venv/Scripts/python -m mypy app

## --- Tests ---
test: test-web test-admin test-api test-mobile

test-web:
	npm run test --workspace=apps/web

test-admin:
	npm run test --workspace=apps/admin

test-api:
	cd apps/api && .venv/Scripts/python -m pytest

test-mobile:
	cd apps/mobile && flutter test

analyze-mobile:
	cd apps/mobile && flutter analyze

## --- Formatting ---
format:
	npm run format
	cd apps/api && .venv/Scripts/python -m ruff format .

format-check:
	npm run format:check
	cd apps/api && .venv/Scripts/python -m ruff format --check .

## --- Database migrations (see docs/migration-guidelines.md) ---
db-upgrade:
	cd apps/api && .venv/Scripts/python -m alembic upgrade head

db-downgrade:
	cd apps/api && .venv/Scripts/python -m alembic downgrade -1

db-history:
	cd apps/api && .venv/Scripts/python -m alembic history

db-current:
	cd apps/api && .venv/Scripts/python -m alembic current

db-revision:
	cd apps/api && .venv/Scripts/python -m alembic revision --autogenerate -m "$(m)"
