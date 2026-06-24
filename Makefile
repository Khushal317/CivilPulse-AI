PNPM ?= pnpm
PYTHON ?= python3

.PHONY: install dev backend-dev frontend-dev lint typecheck test check

install:
	$(PYTHON) -m venv backend/.venv
	backend/.venv/bin/python -m pip install --upgrade pip
	backend/.venv/bin/python -m pip install -e "backend[dev]"
	$(PNPM) --dir frontend install

dev:
	docker compose up --build

backend-dev:
	cd backend && .venv/bin/uvicorn app.main:app --reload

frontend-dev:
	$(PNPM) --dir frontend dev

lint:
	backend/.venv/bin/ruff check backend
	$(PNPM) --dir frontend lint

typecheck:
	backend/.venv/bin/mypy backend/app
	$(PNPM) --dir frontend typecheck

test:
	backend/.venv/bin/pytest backend
	$(PNPM) --dir frontend test

check: lint typecheck test

