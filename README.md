# kyomei_api

FastAPI backend-for-frontend (BFF) for [`kyomei_0`](../kyomei_0). Owns
server-side anime data orchestration — AniList primary, Jikan fallback on
error/timeout — plus shared caching, mirroring the frontend's existing
`animeProvider.ts` provider/fallback pattern. See `CONTRACT.md` for the
authoritative HTTP contract and `CLAUDE.md` for architecture notes.

This project uses [`uv`](https://docs.astral.sh/uv/) instead of poetry/pip:
it's a single fast tool for dependency resolution, virtualenv management, and
running scripts, with lockfile support built in.

Common commands are also wrapped in a [`justfile`](https://github.com/casey/just)
(a `just`-based task runner: no compiled artifacts to track, cleaner recipe
syntax than Make, and self-documenting via `just --list`). Install `just`
once via `winget install --id Casey.Just` or `scoop install just`, then use
the recipes below, or fall back to the underlying `uv run ...` commands
directly if you don't want to install it.

Logging uses stdlib `logging`, configured once at startup — this project is
small enough that a structured logging library would be unneeded overhead.

## Local development

```
uv sync            # install dependencies

just run            # uv run uvicorn app.main:app --reload
just test           # uv run pytest
just lint           # uv run ruff check
just format         # uv run ruff format
```

Copy `.env.example` to `.env` and adjust values as needed before running the
server.
