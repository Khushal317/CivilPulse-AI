# Reporting Workflow

Phase 4 keeps report creation private until the citizen explicitly publishes
the reviewed result.

## Lifecycle

1. The browser validates the required photo, description, and location.
2. `POST /api/v1/reports/analyze` verifies the image's actual content, stores it
   under a server-generated key, and sends the permitted report context to the
   configured analyzer.
3. The analyzer returns a strict structured result. The backend validates it
   again before saving a temporary `issue_drafts` record.
4. The citizen can load, edit, or cancel the draft before its expiry time.
5. `POST /api/v1/reports/{draft_id}/publish` creates the public issue and its
   initial Reported timeline entry in one transaction.
6. Repeating the publish request returns the same issue instead of creating a
   duplicate.

## Privacy Boundary

The analysis input contains the image, description, location, landmark,
optional category, and optional urgency note. Citizen name and contact details
are stored only in the private draft and are excluded from:

- Gemini requests
- public issue response schemas
- application log context

## Analysis Providers

`AI_PROVIDER=demo` is the development default. It produces deterministic,
schema-valid analysis without an external request.

`AI_PROVIDER=gemini` uses the Google Gen AI SDK with:

- a backend-only API key
- a versioned system prompt
- structured JSON output validated by Pydantic
- bounded attempts
- a configured timeout
- safe provider error responses

Production configuration rejects the demo provider.

## Image Storage

The storage service has a provider-neutral interface:

- `local` writes atomically to the configured development storage directory.
- `gcs` writes to the configured Google Cloud Storage bucket.

Only verified JPEG, PNG, and WebP images are accepted. Byte and decoded-pixel
limits protect the API from oversized or decompression-heavy files. Client
filenames are never used as storage keys.

## Failure Behavior

- Invalid images are rejected before analysis.
- Failed or malformed analysis never creates a public issue.
- Drafts remain private until publication succeeds.
- Expired and cancelled drafts cannot be published.
- If publication fails, the transaction is rolled back and the draft remains
  recoverable unless it has expired.
