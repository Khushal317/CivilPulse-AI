# CivicPulse API

FastAPI service for CivicPulse AI.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
```

Health endpoints:

- `GET /health/live`
- `GET /health/ready`

