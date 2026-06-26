# Public Tracker

Phase 5 exposes published civic issues as a privacy-safe, paginated public
catalogue.

## API

`GET /api/v1/issues` accepts:

- `page` — one-based page number
- `page_size` — 1 to 50, default 12
- `category`
- `severity`
- `status`
- `location` — case-insensitive partial location search
- `sort` — `newest`, `oldest`, `most_verified`, or `severity`

Every sort includes deterministic creation-time and UUID tie-breakers so
unchanged data produces stable page boundaries. Verification count includes
only persisted `saw_this_too` actions; advisory fixed or incorrect signals are
not counted.

The list response intentionally excludes original descriptions, AI internals,
citizen names, citizen contact information, and storage keys.

## Frontend

The tracker uses URL search parameters as the source of truth. Filter changes
reset to page one, while pagination preserves every active filter. Filtered
views survive refreshes, browser navigation, bookmarks, and shared links.

The responsive layout uses three columns on large screens, two on tablets, and
one on mobile. Loading, empty, filtered-empty, updating, and API failure states
remain usable without replacing the filter controls.

## Demo Data

After the Docker stack is running:

```bash
docker compose exec backend python -m scripts.seed_demo
```

The command creates 14 deterministic reports, local placeholder images, mixed
statuses and severities, and varied confirmation counts. It is idempotent.
