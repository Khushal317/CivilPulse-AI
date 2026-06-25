# Backend Architecture

## Request Flow

```text
FastAPI route
  → service
  → repository
  → SQLAlchemy session
  → PostgreSQL
```

- Routes translate HTTP requests and responses.
- Services own product and lifecycle rules.
- Repositories isolate persistence queries.
- `get_db_session` supplies one transaction per request, commits successful work, rolls back failures, and always closes the session.
- Models define persistence shape; Pydantic schemas define API shape. They are intentionally separate.

## Data Safety

- Public issue schemas exclude citizen name, contact information, internal image keys, AI model identifiers, and prompt versions.
- Admin schemas may expose private fields only through future authenticated admin routes.
- UUIDs are database identifiers; `public_reference` is the citizen-facing reference.
- Status history and community actions are separate append-only records.
- Community action uniqueness is enforced in PostgreSQL, not only in application code.

## Operations

- Every response receives an `X-Request-ID`.
- A client-provided `X-Request-ID` is preserved for tracing.
- Logs are JSON and include request ID, path, method, status, and duration.
- Expected failures use a stable error envelope.
- Readiness checks require PostgreSQL to be reachable and migrated to the application’s expected revision.

## Migration Rules

- Never edit a migration that has been deployed to a shared environment.
- Generate a new revision for every schema change.
- Review generated SQL before applying it.
- Production migrations run as a controlled deployment step, not independently in each web worker.
- PostgreSQL is the only supported database; SQLite is intentionally not used as a compatibility layer.
