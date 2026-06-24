# Deployment Notes

## Confirmed Architectural Constraint

Google AI Studio is used to prototype Gemini prompts and obtain Gemini API access. CivicPulse also requires a persistent FastAPI process, PostgreSQL, and durable image storage. These server-side requirements must not be placed in browser-generated AI Studio code.

The production-compatible Google architecture is:

- React frontend: a supported AI Studio publishing target or a static/container host
- FastAPI backend: Google Cloud Run
- PostgreSQL: Google Cloud SQL for PostgreSQL
- Images: Google Cloud Storage
- Secrets: Google Secret Manager

The application remains containerized and provider-neutral so the final target can change without changing domain logic.

## Phase 1 Deployment Validation

Phase 1 validates deployability through production container builds and health endpoints. A live Google deployment requires a stakeholder-owned Google Cloud project, billing, IAM permissions, and approved credentials; those external resources are intentionally not created from a local development workspace.

Before production release:

1. Confirm whether “deploy through Google AI Studio” means AI Studio Build mode publishing or using AI Studio for the Gemini integration.
2. Confirm the stakeholder’s Google Cloud project and region.
3. Confirm billing and IAM access.
4. Deploy the backend container to Cloud Run.
5. Attach Cloud SQL and Secret Manager.
6. Configure Cloud Storage and CORS.
7. Point the frontend API base URL to Cloud Run.
8. Run smoke tests against `/health/live`, `/health/ready`, and the frontend.

