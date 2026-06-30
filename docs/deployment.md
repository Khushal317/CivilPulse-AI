# CivicPulse AI Deployment and Handover

This guide documents the production-ready deployment path for CivicPulse AI. It is
provider-conscious but keeps the application portable: the frontend and backend
are containerized, PostgreSQL is the database, and image storage is accessed
through the storage abstraction.

## Confirmed architecture

Google AI Studio is used for Gemini prompt development and Gemini API access.
CivicPulse AI also requires a persistent FastAPI backend, PostgreSQL, and durable
object storage. Those server-side components should not be embedded into
browser-only AI Studio code.

Recommended Google production architecture:

- Frontend: AI Studio-supported publishing target, static hosting, or the
  production frontend container.
- Backend: Cloud Run running the FastAPI production image.
- Database: Cloud SQL for PostgreSQL.
- Image storage: Cloud Storage.
- Secrets: Secret Manager.
- TLS/HTTPS: managed by the frontend host and Cloud Run/load balancer.

If the stakeholder requires a different interpretation of “deploy through Google
AI Studio,” record the exact workflow, limitations, and final URLs in this file.

## Required production values

Use `.env.production.example` as the source of truth for environment names.
Production secrets should be stored in the deployment platform secret manager,
not in a checked-in `.env` file.

Critical production requirements enforced by the backend:

- `APP_ENV=production`
- `AI_PROVIDER=gemini`
- `GEMINI_API_KEY` configured server-side only
- `CORS_ORIGINS` uses explicit HTTPS origins only
- `DATABASE_URL` points to managed PostgreSQL
- `STORAGE_BACKEND=gcs`
- `STORAGE_BUCKET` configured
- `ADMIN_PASSWORD_HASH` configured
- `ADMIN_SESSION_SECRET` changed from local default
- `ANONYMOUS_ACTOR_SECRET` changed from local default

Frontend build-time values:

- `VITE_API_BASE_URL` points to the public backend URL
- `VITE_GOOGLE_MAPS_API_KEY` uses a browser-visible Google Maps key restricted
  by HTTP referrer to the production frontend domain

## Production image builds

Backend:

```bash
docker build --target production -t civicpulse-backend:release ./backend
```

Frontend:

```bash
docker build \
  --target production \
  --build-arg VITE_API_BASE_URL=https://replace-with-api.example.com \
  --build-arg VITE_GOOGLE_MAPS_API_KEY=replace-with-referrer-restricted-key \
  -t civicpulse-frontend:release \
  ./frontend
```

The frontend container serves on port `8080` and exposes `/health`.
The backend production image serves FastAPI on port `8000`.

## Controlled migration step

Run migrations once per release before shifting production traffic to the new
backend image:

```bash
alembic -c alembic.ini upgrade head
```

For Cloud Run, run this as a dedicated job/container execution using the same
backend image and production database secrets. Do not rely on every web worker
running migrations at startup.

Verification:

```bash
curl -fsS https://replace-with-api.example.com/health/ready
```

`/health/ready` checks both the expected Alembic revision and image storage
health, so it should fail if the database is not migrated or storage is not
available.

## Smoke tests

After deployment and migration, run the read-only smoke script:

```bash
cd backend
python -m scripts.smoke_deployment \
  --api-base-url https://replace-with-api.example.com \
  --frontend-url https://replace-with-frontend.example.com
```

The smoke script verifies:

- frontend root loads
- frontend `/health` loads
- backend `/health/live` loads
- backend `/health/ready` loads
- public issues API responds
- public areas API responds

Manual smoke pass:

1. Open the homepage.
2. Open Public Tracker List View and Map View.
3. Open one issue detail page.
4. Submit one non-production test report only if the environment allows test
   data, then cancel or clean it up.
5. Sign in to the admin panel.
6. Run the Civic Operations Agent.
7. Confirm generated reports show `gemini-2.5-flash` when Gemini is reachable.

## Backup and restore

Database backup:

- Enable automated Cloud SQL backups.
- Enable point-in-time recovery if the production budget allows it.
- Before major releases, take an on-demand backup/snapshot.

Manual logical backup example:

```bash
pg_dump "$DATABASE_URL" --format=custom --file=civicpulse-$(date +%Y%m%d%H%M).dump
```

Restore drill example:

```bash
createdb civicpulse_restore_check
pg_restore --dbname=civicpulse_restore_check --clean --if-exists civicpulse-backup.dump
```

Object storage backup:

- Enable Cloud Storage object versioning or lifecycle rules appropriate to the
  deployment budget.
- Keep the bucket in the same region family as the backend/database when
  possible.
- Verify that at least one uploaded issue image can be read after a deployment.

Backup restoration is considered demonstrated only after a database backup has
been restored to a separate database and `/health/ready` passes against that
restored database with a safe non-production backend.

## Rollback procedure

Safe application rollback:

1. Keep the previous backend and frontend image tags.
2. If the new release fails before migration, redeploy the previous images.
3. If the new release fails after a backward-compatible migration, redeploy the
   previous images and keep the migrated database.
4. If the migration is not backward-compatible, restore the pre-release database
   backup and redeploy the previous images.
5. Run smoke tests again.

Rules:

- Never run destructive database commands without a backup.
- Never roll back storage buckets by deleting current production images.
- Document the incident, image tags, database backup used, and final status.

## Admin operation handover

Before handing over production:

1. Generate and store the admin password hash:

   ```bash
   cd backend
   .venv/bin/python -m scripts.hash_admin_password
   ```

2. Store the hash in `ADMIN_PASSWORD_HASH`.
3. Store `ADMIN_SESSION_SECRET` in Secret Manager.
4. Confirm `/admin/login` works over HTTPS.
5. Confirm the admin can:
   - view dashboard metrics
   - inspect issue details
   - update status
   - run operations analysis
   - review draft missions
   - publish/delete missions

## Security and privacy release checks

Run before every public deployment:

```bash
git grep -n -E 'AIza|AQ\\.|GEMINI_API_KEY=.+[^=]$|ADMIN_PASSWORD_HASH=.+[^=]$' -- \
  ':(exclude).env.example' \
  ':(exclude).env.production.example' \
  ':(exclude)docs/deployment.md'
```

Expected result: no real secrets in tracked source files.

Also verify:

- public issue APIs do not return citizen contact fields
- admin cookies are `HttpOnly`, `SameSite=Strict`, and `Secure` in production
- anonymous actor cookies are `HttpOnly` and `Secure` in production
- browser-visible Google Maps key is referrer-restricted
- backend-only Gemini key is not present in frontend bundles

## Gemini model and prompt versioning

Current production target:

- Model: `gemini-2.5-flash`
- Issue-report prompt version: `civic-report-v1`
- Mission/operations prompts are versioned in code by service class and model
  output schema.

When changing models or prompts:

1. Update the relevant service prompt/schema.
2. Add or update tests for parsing, malformed output, and fallback behavior.
3. Update `AI_PROMPT_VERSION` when the public report-analysis contract changes.
4. Record the deployed model in release notes.

## Deployment checklist ownership

Items requiring external resources cannot be completed from a local development
workspace:

- stakeholder confirmation of Google AI Studio publishing workflow
- managed PostgreSQL provisioning
- production object storage provisioning
- HTTPS domain setup
- database backup/restore drill
- production smoke tests against live URLs

Those items should be checked in `CHECKLIST.md` only after the production
environment exists and the evidence is recorded.
