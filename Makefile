.PHONY: lint typecheck test run-api migrate

lint:
	ruff check .

typecheck:
	mypy libs services modules apps/api-gateway

test:
	pytest

run-api:
	uvicorn main:app --app-dir apps/api-gateway --host 0.0.0.0 --port 8080

migrate:
	alembic upgrade head
