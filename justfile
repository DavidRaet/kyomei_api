run:
    uv run python -m uvicorn app.main:app --reload

test:
    uv run python -m pytest

lint:
    uv run ruff check

format:
    uv run ruff format

hooks-install:
    uv run pre-commit install

hooks-run:
    uv run pre-commit run --all-files
