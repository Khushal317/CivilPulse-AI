# Security and Reliability Notes

Phase 9 hardens the MVP around abuse prevention, safe storage, dependency readiness,
and leak prevention. The app is still an MVP, but the core controls are now explicit
and test-covered.

## Request abuse controls

- Report analysis is rate limited per client IP before image storage and AI analysis.
- Community actions are rate limited per anonymous actor hash.
- Admin login is rate limited per client IP and only records failed attempts.
- Pagination limits are enforced on public tracker and admin queue endpoints.

The current rate limiters are in-process. That is acceptable for local and single-node
MVP deployments. A multi-instance deployment should move these counters to Redis or
another shared store without changing the route contracts.

## Upload and image storage controls

- Uploaded images are read with a server-side byte cap.
- Pillow verifies actual image content; filenames and browser-provided content types are
not trusted.
- Only JPEG, PNG, and WebP are accepted.
- Stored image keys are generated UUID names under the `issues/` prefix.
- Local storage rejects absolute paths and `..` path traversal.
- Media responses are served through the API only and include `X-Content-Type-Options:
  nosniff`.
- Storage failures return safe user-facing errors without exposing filesystem or bucket
details.

## Authentication, cookies, and CSRF

- Admin sessions use random opaque cookies. Only SHA-256 token hashes are stored.
- Admin cookies are `HttpOnly`, `SameSite=Strict`, and `Secure` in production.
- Anonymous actor cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- Admin state-changing requests require the derived `X-CSRF-Token`.

## Secrets and private fields

- Production rejects default local admin/session/anonymous secrets.
- Production rejects demo AI mode and localhost, wildcard, or plain HTTP CORS origins.
- Vite only exposes `VITE_` variables to the frontend; server secrets remain backend-only.
- Public issue list/detail schemas do not include `citizen_name`, `citizen_contact`,
  `image_key`, AI model metadata, session tokens, or API keys.
- Structured logs redact fields whose names include password, secret, key, token, session,
  csrf, cookie, authorization, or contact.

## Dependency failure handling

- `/health/live` checks process liveness.
- `/health/ready` checks the database migration revision and image storage health.
- SQLAlchemy failures are converted to safe `database_unavailable` responses.
- Gemini transport failures are converted to safe `ai_unavailable` responses.
- Invalid Gemini structured responses are converted to `ai_invalid_response`.
- Storage read/write/delete failures are converted to safe `storage_unavailable` responses.

## Cleanup operations

Expired unpublished report drafts and their images can be removed with:

```bash
cd backend
.venv/bin/python -m scripts.cleanup_abandoned_data
```

The same command also removes images in storage that are no longer referenced by either
drafts or published issues. Use `--skip-unused-images` if you only want expired draft
cleanup.

## Database indexes reviewed

Existing indexes cover tracker filtering, draft expiry lookup, issue update timelines,
admin session activity, and community counts. Phase 9 adds:

- `ix_community_actions_actor_created` for community action rate-limit checks.
- `ix_issues_admin_updated` for admin issue queue ordering.
- `ix_issues_priority_queue` for high-priority dashboard queues.

## Remaining production notes

- Replace in-process rate limiters with a shared store before running multiple backend
  instances.
- Rotate any development Gemini or GitHub tokens before real public deployment.
- Configure HTTPS-only production origins in `CORS_ORIGINS`.
- Run the cleanup script from cron, a worker, or a managed scheduled job.
