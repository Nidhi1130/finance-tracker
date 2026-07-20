.PHONY: backend-dev backend-test

backend-dev:
	cd backend && UV_CACHE_DIR=/private/tmp/uv-cache uv run uvicorn app.main:app --reload

backend-test:
	cd backend && UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest
