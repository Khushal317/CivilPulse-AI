# Testing and Acceptance Notes

Phase 10 proves the MVP through automated backend tests, frontend route/component tests,
PostgreSQL migration checks, production builds, and a live browser smoke pass.

## Automated backend coverage

- Domain enum and schema validation.
- Database constraints and Alembic upgrade/downgrade behavior.
- Report draft analysis, editing, cancellation, publication, expiry, and idempotency.
- Gemini structured-output parsing, malformed output, and transport failure handling with
  controlled fakes.
- Image validation, safe storage names, traversal protection, storage health, and cleanup.
- Public tracker filtering, sorting, pagination, privacy guarantees, and community signals.
- Verification promotion after three distinct confirmations.
- Admin authentication, session expiry/revocation, dashboard aggregates, and status
  transition rules.
- Complete pothole-near-school acceptance flow:
  report draft -> publish -> three confirmations -> Community Verified -> Escalated ->
  In Progress -> Resolved -> public timeline.

## Automated frontend coverage

- Report form validation, AI submit loading/success/failure paths, review editing,
  cancellation, and publication success.
- Public tracker filters, search, pagination, empty states, and error states.
- Issue detail rendering, community action feedback, rejected-state behavior, and timeline.
- Admin login, protected routes, dashboard, issue queue, and status update flow.
- Shared UI accessibility contracts for labels, hints, errors, buttons, dialogs, badges,
  loading states, and error states.
- Route-level acceptance flow:
  report -> review -> publish -> tracker -> issue detail -> resolved public timeline.

## Production-like checks

- PostgreSQL-marked Alembic migration test runs against a dedicated `civicpulse_test`
  database.
- Local object storage behavior is covered by integration tests and readiness checks.
- Frontend production build passes.
- Backend readiness checks pass against the running Docker stack.

## Live browser smoke pass

Checked pages:

- `/` at 1280x800 desktop.
- `/issues` at 768x900 tablet.
- `/report` at 390x844 mobile.
- `/admin/login` at 390x844 mobile.
- `/not-a-real-page` at 1280x800 desktop.

Results:

- Expected page titles and headings rendered.
- No horizontal overflow detected at tested viewports.
- No browser console warnings or errors were observed.
- Skip link and primary focusable navigation/control order exist in the DOM.

Browser automation note: the in-app browser API did not advance focus with Tab during the
smoke pass, so keyboard behavior is covered by DOM contract checks and automated component
accessibility tests. A human keyboard-only pass should still be repeated before public launch.

## Acceptance command set

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/mypy app scripts
```

```bash
docker compose exec frontend npm test -- --run
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm run build
```

```bash
docker compose exec backend sh -lc \
  'TEST_DATABASE_URL=postgresql+psycopg://civicpulse:civicpulse-local@postgres:5432/civicpulse_test pytest -q -m postgres'
curl -sS -i http://localhost:8000/health/ready
```

## Remaining launch notes

- Repeat a human keyboard-only pass in a real browser before public launch.
- Run a full manual report submission with Gemini enabled when API quota and test data are
  acceptable.
- Repeat PostgreSQL and object storage checks against managed production services during
  Phase 11 deployment.
