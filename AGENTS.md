# Agent Notes

## Project Shape

- Backend: FastAPI app under `apps/backend`, served from `apps.backend.app.main:app`.
- Frontend: Next.js app under `apps/frontend`.
- Runtime data lives under `data/` and is ignored by git.

## Local Commands

- Install backend dependencies: `.venv/bin/python -m pip install -e '.[backend,dev]'`.
- Install frontend dependencies: `cd apps/frontend && npm install`.
- Backend tests: `.venv/bin/python -m pytest -q`.
- Backend lint: `.venv/bin/python -m ruff check .`.
- Frontend typecheck: `cd apps/frontend && npm run typecheck`.
- Frontend lint: `cd apps/frontend && npm run lint`.
- Frontend build: `cd apps/frontend && npm run build`.
- Start stack: `make start`.
- Stop stack: `make stop`.

## Ports

- SurrealDB: `8000`.
- Backend API: `8001`.
- Frontend: `3001`.

## Notes

- The frontend API client defaults to `http://127.0.0.1:8001/api/v1`.
- Makefile prefers repo-local `.venv/bin/python`; create `.venv` before starting if it is missing.
