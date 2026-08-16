# kyomei_api

FastAPI backend-for-frontend (BFF) for [`kyomei_0`](../kyomei_0). Owns
server-side anime data orchestration — AniList primary, Jikan fallback on
error/timeout — plus shared caching, mirroring the frontend's existing
`animeProvider.ts` provider/fallback pattern. See `CONTRACT.md` for the
authoritative HTTP contract and `CLAUDE.md` for architecture notes.

This project uses [`uv`](https://docs.astral.sh/uv/) instead of poetry/pip:
it's a single fast tool for dependency resolution, virtualenv management, and
running scripts, with lockfile support built in.

## Local development

```
uv sync                              # install dependencies
uv run uvicorn app.main:app --reload # run the dev server
uv run pytest                        # run all tests
uv run ruff check                    # lint
uv run ruff format                   # format
```

Copy `.env.example` to `.env` and adjust values as needed before running the
server.
