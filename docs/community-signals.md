# Issue Details and Community Signals

Phase 6 provides the public issue record, status history, and account-free
community observations.

## Public Detail

`GET /api/v1/issues/{issue_id}` returns:

- the full public issue image and reference
- citizen description and AI-structured complaint
- location, category, severity, urgency, department, and safety guidance
- chronological public timeline entries and notes
- calculated counts for all four community actions
- the actions already submitted by the current anonymous browser

Citizen identity, contact details, AI model metadata, prompt version, and
storage keys remain private.

## Anonymous Browser Identifier

FastAPI creates a random browser identifier and signs it with HMAC-SHA256 using
`ANONYMOUS_ACTOR_SECRET`. The signed identifier is stored in an HttpOnly,
SameSite=Lax cookie. The database receives only a SHA-256 hash, never the raw
identifier or signature.

A unique database constraint allows each browser to submit each action type
once per issue. Repeated submissions are successful but return
`accepted: false` and do not change counts.

## Community Actions

- `saw_this_too` confirms that the issue is present.
- `still_unresolved` reports that the problem remains.
- `fixed` is advisory and never sets official Resolved status.
- `incorrect` flags a possible duplicate or inaccurate report.

Rejected issues do not accept community actions. Other statuses can collect
advisory signals, but only an issue currently in Reported status can be
automatically promoted.

## Automatic Promotion

After the third distinct `saw_this_too` confirmation:

1. The Reported issue is locked for the transaction.
2. Its status changes to Community Verified.
3. One system timeline entry records the promotion.
4. Later confirmations update the count without creating more promotion events.

## Rate Limiting

The backend limits total community-action submissions per anonymous actor over
a configurable time window. Duplicate submissions are checked before the rate
limit so harmless retries remain idempotent.
