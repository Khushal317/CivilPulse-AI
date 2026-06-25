# CivicPulse AI

CivicPulse AI turns citizen-submitted photos and descriptions into structured, publicly trackable civic issues.

The repository is organized as a React frontend, FastAPI backend, PostgreSQL database, and provider-neutral infrastructure configuration. Product and implementation decisions are recorded in [implementation.md](implementation.md), and progress is tracked in [CHECKLIST.md](CHECKLIST.md).

## Prerequisites

- Docker Desktop with Docker Compose, or:
  - Python 3.12+
  - Node.js 22+
  - pnpm 10+
  - PostgreSQL 17+

## Start with Docker

1. Copy `.env.example` to `.env`.
2. Replace the local PostgreSQL password in `.env`.
3. Run:

   ```bash
   docker compose up --build
   ```

   Docker Compose waits for PostgreSQL, applies Alembic migrations, and then starts the API and frontend.

4. Open:
   - Frontend: <http://localhost:5173>
   - API documentation: <http://localhost:8000/docs>
   - API readiness: <http://localhost:8000/health/ready>

## Start without Docker

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e "backend[dev]"
pnpm --dir frontend install
```

Start the backend:

```bash
cd backend
.venv/bin/alembic -c alembic.ini upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
pnpm --dir frontend dev
```

The frontend reads `VITE_API_BASE_URL` and defaults to `http://localhost:8000`.

## Database Migrations

Create PostgreSQL and set `DATABASE_URL`, then run migrations from the repository root:

```bash
make migrate
```

Useful direct commands:

```bash
cd backend
.venv/bin/alembic -c alembic.ini current
.venv/bin/alembic -c alembic.ini upgrade head
.venv/bin/alembic -c alembic.ini downgrade -1
```

`/health/live` confirms the API process is running. `/health/ready` returns success only when PostgreSQL is reachable and its Alembic revision matches the application.

## Quality Checks

```bash
make lint
make typecheck
make test
make check
```

## Environment Rules

- Never commit `.env`.
- Browser-visible configuration must use the `VITE_` prefix.
- Gemini credentials are backend-only.
- `.env.example` documents names and safe placeholders, not real credentials.

## Reporting Configuration

Phase 4 supports two analysis modes:

- `AI_PROVIDER=demo` uses deterministic local analysis for development and tests.
- `AI_PROVIDER=gemini` sends the image and civic-issue text to Gemini using the
  backend-only `GEMINI_API_KEY`.

Uploaded images use `STORAGE_BACKEND=local` by default. Production deployments
can use `STORAGE_BACKEND=gcs` with `STORAGE_BUCKET` configured. See
`docs/reporting-workflow.md` for the request lifecycle, privacy boundary, and
failure behavior.

## Current Phase

Phase 4 implements the private report draft workflow: validated image upload,
AI-assisted structuring, citizen review and editing, cancellation, draft expiry,
and idempotent publication with an initial Reported timeline entry.
