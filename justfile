run:
    uv run uvicorn app.main:app --reload

test:
    uv run pytest

lint:
    uv run ruff check

format:
    uv run ruff format
