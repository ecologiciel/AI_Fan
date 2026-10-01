.PHONY: up down test lint type-check web-check

up:
	docker compose up --build

down:
	docker compose down

test:
	cd apps/api && python -m pytest tests

lint:
	cd apps/api && python -m ruff check app tests
	python -m ruff check apps/worker

type-check:
	cd apps/api && python -m mypy app
	MYPYPATH=apps/api python -m mypy apps/worker/worker

web-check:
	cd apps/web && npm ci && npm run lint && npm run type-check && npm run build
