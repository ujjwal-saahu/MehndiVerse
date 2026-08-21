# MehndiVerse

MehndiVerse is a marketplace and design-discovery platform connecting customers with mehndi artists. See [docs/project-flow-diagram.md](docs/project-flow-diagram.md) for a visual overview, [docs/product-requirements.md](docs/product-requirements.md) for product scope, and [docs/system-architecture.md](docs/system-architecture.md) for the target architecture.

This repository is being built incrementally, one phase at a time. See [docs/development-roadmap.md](docs/development-roadmap.md) for the phase plan. **This is Phase 1: monorepo and engineering foundation.** No authentication or product features are implemented yet — every app exposes only a health check.

## Repository layout

```
mehndi-verse/
├── apps/
│   ├── mobile/     # Flutter customer + artist app
│   ├── web/        # Next.js customer web app
│   ├── admin/      # Next.js admin dashboard
│   └── api/        # FastAPI backend
├── packages/
│   ├── contracts/      # Shared TypeScript types (e.g. health-check shape) used by web + admin
│   ├── design-tokens/  # Shared placeholder design tokens used by web + admin
│   └── config/         # Shared TypeScript/ESLint base config used by web + admin
├── infrastructure/  # Reserved for IaC / deployment config (empty at Phase 1)
├── docs/             # Product, architecture, and process documentation
├── scripts/          # Reserved for repo automation scripts (empty at Phase 1)
├── .github/workflows/ # CI
├── docker-compose.yml # Local Postgres + Redis + API
├── Makefile           # Convenience targets (requires GNU make)
└── .env.example        # Root-level env vars for docker-compose
```

## Prerequisites

* Node.js 24+ and npm 11+
* Python 3.12+ (this repo was scaffolded and verified against 3.14)
* [Flutter SDK](https://docs.flutter.dev/get-started/install) (stable channel; verified against 3.44.6)
* Docker Desktop (for Postgres/Redis/API containers)
* GNU make (optional — the `Makefile` targets are convenience wrappers; every target's underlying command is also documented below and can be run directly)

## Local setup

Run once after cloning:

```bash
# 1. Install JS dependencies for web, admin, and shared packages (npm workspaces)
npm install

# 2. Set up the FastAPI backend virtual environment
cd apps/api
python -m venv .venv
# Windows:
.venv/Scripts/python -m pip install -e ".[dev]"
# macOS/Linux:
# .venv/bin/python -m pip install -e ".[dev]"
cd ../..

# 3. Fetch Flutter dependencies
cd apps/mobile
flutter pub get
# Regenerate freezed/json_serializable code after model changes:
dart run build_runner build --delete-conflicting-outputs
cd ../..

# 4. Copy environment examples (never commit the resulting .env files)
cp .env.example .env
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
cp apps/admin/.env.example apps/admin/.env.local

# 5. Apply database migrations (with Postgres up — see "Running services locally")
cd apps/api && .venv/Scripts/python -m alembic upgrade head
```

Equivalent single command: `make setup` (steps 1–3; still copy the env files manually and run `make db-upgrade`).

## Running services locally

```bash
# Postgres + Redis (+ the containerized API) via Docker
docker compose up -d postgres redis      # or: make docker-up
docker compose up -d api                  # once apps/api/.env exists, or run the API natively below

# FastAPI backend natively (auto-reload)
cd apps/api && .venv/Scripts/uvicorn app.main:app --reload   # make api-dev

# Next.js customer web app
npm run dev --workspace=apps/web          # make web-dev

# Next.js admin dashboard
npm run dev --workspace=apps/admin        # make admin-dev

# Flutter mobile app
cd apps/mobile && flutter run
```

## Verification commands

Every command below is what CI runs (see `.github/workflows/`).

| Check | Command | Make target |
|---|---|---|
| Web lint | `npm run lint --workspace=apps/web` | `make lint-web` |
| Web typecheck | `npm run typecheck --workspace=apps/web` | `make typecheck-web` |
| Web tests | `npm run test --workspace=apps/web` | `make test-web` |
| Admin lint | `npm run lint --workspace=apps/admin` | `make lint-admin` |
| Admin typecheck | `npm run typecheck --workspace=apps/admin` | `make typecheck-admin` |
| Admin tests | `npm run test --workspace=apps/admin` | `make test-admin` |
| API lint | `cd apps/api && .venv/Scripts/python -m ruff check .` | `make lint-api` |
| API typecheck | `cd apps/api && .venv/Scripts/python -m mypy app migrations` | `make typecheck-api` |
| API tests (needs Postgres up) | `cd apps/api && .venv/Scripts/python -m pytest` | `make test-api` |
| Mobile analyze | `cd apps/mobile && flutter analyze` | `make analyze-mobile` |
| Mobile tests | `cd apps/mobile && flutter test` | `make test-mobile` |
| Docker Compose config | `docker compose config` | `make docker-config` |
| Format (write) | `npm run format` + `ruff format .` in `apps/api` | `make format` |
| Format (check) | `npm run format:check` + `ruff format --check .` in `apps/api` | `make format-check` |

## Health checks

* Backend: `GET /health` on the FastAPI app — reports overall status plus Postgres/Redis reachability.
* Web: `GET /api/health` — confirms the Next.js server process is up.
* Admin: `GET /api/health` — same, for the admin app.

## Database

The schema (41 tables) and migrations live in `apps/api/app/db/` and `apps/api/migrations/`. See [docs/database-schema.md](docs/database-schema.md) for conventions, [docs/database-relationships.md](docs/database-relationships.md) for how the tables relate, [docs/booking-status-rules.md](docs/booking-status-rules.md) for the booking state machine, and [docs/migration-guidelines.md](docs/migration-guidelines.md) for how to write and run migrations.

```bash
make db-upgrade      # apply all migrations
make db-downgrade    # roll back the most recent migration
make db-current      # show the currently applied revision
make db-history      # list all revisions
```

## Secrets

No `.env` file is ever committed — only `.env.example` files with placeholder values. See [docs/security-baseline.md](docs/security-baseline.md) for the full secrets-handling policy.

## Documentation

Start with [docs/product-requirements.md](docs/product-requirements.md), [docs/user-roles-and-permissions.md](docs/user-roles-and-permissions.md), [docs/feature-scope.md](docs/feature-scope.md), [docs/system-architecture.md](docs/system-architecture.md), [docs/development-roadmap.md](docs/development-roadmap.md), [docs/security-baseline.md](docs/security-baseline.md), and [docs/decisions/0001-technology-stack.md](docs/decisions/0001-technology-stack.md).
