# CivicPulse Map View Configuration

The Map View integration uses Google Maps only for a small public-tracker enhancement:

- Places Autocomplete on the report location field.
- Latitude and longitude capture for selected places.
- Public issue markers in the tracker Map View.

No backend Google Maps key is required for this phase.

## Environment variable

Add this to `.env` for local development:

```bash
VITE_GOOGLE_MAPS_API_KEY=your-google-maps-browser-key
```

The key is browser-visible because Google Maps JavaScript and Places Autocomplete run in the frontend. Restrict the key in Google Cloud instead of treating it like a backend secret.

Recommended Google Cloud restrictions:

- Application restriction: HTTP referrers
- Local referrers:
  - `http://localhost:5173/*`
  - `http://127.0.0.1:5173/*`
- Production referrer: the final production domain
- Enabled APIs:
  - Maps JavaScript API
  - Places API

## Failure behavior

The app must continue to work if the key is missing or invalid:

- Report Issue keeps a manual location fallback.
- Public Tracker List View keeps working.
- Map View should show a clear configuration/error state instead of crashing.

## Scope guardrails

Do not add route planning, heatmaps, clustering, radius search, admin GIS tools, Street View, or map analytics in this phase.
