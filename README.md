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
.venv/bin/uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
pnpm --dir frontend dev
```

The frontend reads `VITE_API_BASE_URL` and defaults to `http://localhost:8000`.

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

## Current Phase

Phase 1 establishes the project foundation. Domain models, migrations, Gemini analysis, reporting, tracking, community verification, and admin behavior are implemented in later phases.

