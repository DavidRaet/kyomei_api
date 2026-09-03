# Repository Guidelines

## Project Structure & Module Organization

Kyomei API is a FastAPI backend-for-frontend that uses AniList as its sole upstream source. Application code lives in `app/`: `anime/` contains domain models, errors, and the provider protocol; `anilist/` contains the async GraphQL client; `routers/` contains HTTP schemas and endpoints; and `main.py`, `config.py`, `rate_limit.py`, and `logging_config.py` provide application wiring and middleware. `app/cache/` is reserved for the planned in-memory cache. Tests are in `tests/`; API and product documentation are in `CONTRACT.md` and `docs/`; deployment files include `Dockerfile`, `justfile`, and `.github/workflows/ci.yml`.

Keep `main.py` wiring-only and organize new logic by domain. Treat `CONTRACT.md` as the authoritative HTTP boundary; update it with any endpoint, field, status-code, or error-shape change.

## Build, Test, and Development Commands

Use `uv` for dependency management and the `justfile` for routine tasks:

```text
uv sync                         # install locked dependencies
just run                        # start Uvicorn with reload
just test                       # run the full pytest suite
just lint                       # run Ruff checks
just format                     # format Python files with Ruff
just hooks-install              # install pre-commit hooks
just hooks-run                  # run all hooks manually
docker build -t kyomei-api .    # verify the production image builds
```

Copy `.env.example` to `.env` for local configuration. The API listens on port 8000 by default.

## Coding Style & Naming Conventions

Target Python 3.11+ and use four-space indentation, double quotes, and a 120-character line limit. Ruff enforces pycodestyle, Pyflakes, and import sorting (`E`, `F`, `I`). Use `snake_case` for Python names, `PascalCase` for classes and Pydantic models, and preserve the API’s `camelCase` response fields through the existing schemas.

## Testing Guidelines

Tests use pytest, pytest-asyncio, and respx. Name files `test_*.py` and tests `test_*`. Add focused unit tests for domain/client behavior and router tests for success and mapped error paths; mock AniList calls with respx. Run a single test with `uv run pytest tests/test_health.py::test_health_returns_ok`. All tests and Ruff checks must pass before submitting.

## Commit & Pull Request Guidelines

Use concise conventional-style subjects such as `feat:`, `fix:`, `tests:`, `docs:`, or `config:`. Pull requests should explain the behavior change, identify contract or configuration changes, link relevant issues, and include test commands/results. Include request/response examples or screenshots when changing API-facing behavior. Keep frontend contract changes synchronized with the separate `kyomei_0` repository.

## Security & Configuration

Never commit `.env` or upstream credentials. Review CORS and rate-limit settings when changing middleware, and avoid logging secrets or full upstream payloads.
