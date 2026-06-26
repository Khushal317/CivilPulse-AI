# Administrator Dashboard

Phase 7 provides a deliberately small administrator surface for monitoring and
managing published civic issues.

## Local setup

Set these backend-only values in `.env`:

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH='generated-scrypt-value'
ADMIN_SESSION_SECRET=replace-with-a-long-random-secret
ADMIN_SESSION_TTL_MINUTES=480
ADMIN_LOGIN_RATE_LIMIT=5
ADMIN_LOGIN_RATE_WINDOW_MINUTES=15
```

Generate the password hash interactively:

```bash
cd backend
.venv/bin/python -m scripts.hash_admin_password
```

Open <http://localhost:5173/admin>. The browser is redirected to the login page
when no valid administrator session exists.

## Security boundary

- The plaintext password is never stored.
- The browser receives a random session token in an HttpOnly, Strict SameSite
  cookie. Production cookies also use the Secure flag.
- PostgreSQL stores only a SHA-256 hash of the session token.
- Sessions have a fixed expiry and logout revokes the server-side record.
- Login attempts are rate limited by client address.
- Every administrator API requires authentication.
- Status changes and logout additionally require the session CSRF token.
- Citizen name and contact remain absent from public APIs and are returned only
  by the protected administrator issue-detail endpoint.

## Dashboard and issue workflow

The dashboard shows total, high-severity, community-verified, pending, and
resolved counts, plus category distribution, recent reports, and a priority
queue.

The issue queue supports text search and category, severity, and status
filters. An administrator can inspect the full report, AI audit fields,
community activity, public timeline, and authorized private contact fields.

The backend owns the status-transition rules. Invalid transitions return a
conflict response even if a client bypasses the user interface. Accepted
changes create public timeline entries. Rejection requires a reason; resolving
or rejecting requires an additional confirmation in the web interface.
