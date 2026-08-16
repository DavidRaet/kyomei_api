# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of this repo

**Scaffolding is done; domain logic is not.** `app/` exists with the full planned layout, `pyproject.toml`/`uv.lock` are checked in, CI (lint + test + Docker build) runs on every PR, and the service deploys to Railway. But `app/anime/`, `app/anilist/`, `app/cache/`, `app/routers/`, and `app/config.py` are all **empty stub modules** (a one-line comment describing their intended contents, nothing else). The only thing actually implemented is `GET /health` in `app/main.py` itself. A prior Go scaffold (`go.mod`, `go.sum`) was created and then deleted — see "Why FastAPI, not Go" below — so **do not re-introduce Go tooling** or assume any Go code exists to port.

This maps to `docs/fastapi-backend-setup-checklist.md`: Sections 1, 2, 6, 7, and most of 8 (repo/project structure, dependencies/tooling, containerization, CI/CD, deploy) are checked off. Section 3 (core service implementation), 4 (local dev verification), 5 (testing beyond the health check), 9 (frontend cutover), and 10 (docs) are still open — **this is the actual next-work list**, not just historical context.

Before writing code, read, in this order:
1. `docs/fastapi-backend-setup-checklist.md` — the task list; check which items are still unchecked before assuming something is or isn't built.
2. `CONTRACT.md` — the authoritative HTTP contract with the frontend (`kyomei_0`).
3. `docs/Kyomei-MVP-PRD-v2.1.md` — full product context; most of it (auth, Postgres, recommendations) is **out of scope for this repo's current phase**, but explains where things are headed.

Follow the existing layout under `app/` (see "Architecture" below) rather than inventing a different structure — the module boundaries already exist, they just need implementations filled in.

## Commands

This project uses **`uv`** (not poetry/pip directly). A `justfile` wraps the common ones — prefer `just <target>` over calling `uv run ...` directly:

```
uv sync                                          # install dependencies
just run     # = uv run uvicorn app.main:app --reload
just test    # = uv run pytest
just lint    # = uv run ruff check
just format  # = uv run ruff format

uv run pytest tests/test_health.py::test_health_returns_ok   # run a single test
```

Copy `.env.example` to `.env` before running locally (`PORT`, `ANILIST_ENDPOINT`, `CACHE_TTL_SECONDS` — not yet actually read by any code, since `app/config.py` is still a stub).

Docker: `docker build -t kyomei-api .` / `docker run --rm -p 8000:8000 kyomei-api`. The image uses `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` and installs deps in a separate layer from app code before copying `app/` in, so editing source doesn't invalidate the dependency-install layer. `CMD` reads `$PORT` at runtime (Railway sets this in prod; falls back to 8000 locally) — this only works because it uses the shell form, not exec form.

CI (`.github/workflows/ci.yml`) runs two independent jobs on every PR and on push to `main`: `lint-and-test` (`uv sync`, `ruff check`, `pytest`) and `docker-build` (`docker build` only, no push). See `docs/learning/cicd-notes.md` and `docs/learning/docker-notes.md` for the reasoning behind these setups if you need to modify them.

## Architecture

**This is a BFF (backend-for-frontend), not the recommendation engine described in the PRD.** The PRD (`docs/Kyomei-MVP-PRD-v2.1.md`) describes a much larger eventual system (Auth0, PostgreSQL, ratings, watchlist, recommendations). That is explicitly **out of scope** for the current phase — this repo's job right now is orchestration + caching only, per `docs/fastapi-backend-setup-checklist.md`'s "Notes for Claude Code" section:

- Keep `app/main.py` wiring-only — no business logic.
- Organize real logic under `app/` by *domain* (`anime`, `anilist`, `cache`), not by technical layer.
- This service mirrors the frontend's provider abstraction server-side, not its fallback shape. The frontend (`kyomei_0`, a separate repo) has `src/api/animeProvider.ts` (abstraction point), `src/api/anilist.ts` (data source), and `src/api/cache.ts` (client-side cache). `kyomei_api` uses AniList as its sole upstream data source — a Jikan client was implemented and then removed as a fallback (see `docs/Kyomei-MVP-PRD-v2.1.md`'s Design Decisions for why); don't reintroduce a Jikan client without revisiting that decision.
- Don't add Redis, a database, or auth in this phase, even though the PRD describes them for later phases.
- Favor light async libraries (`httpx`, `cachetools`) over heavier frameworks/ORMs.

Module layout (scaffolded; each non-`main.py` module is currently just a docstring-only stub — read the one-line comment at the top of each `__init__.py` for what belongs there before adding code elsewhere):

```
app/
├── main.py       # FastAPI app creation, router mounting, config load — wiring only. Currently defines GET /health inline; once app/routers/ has real routers, mount them here instead of adding more inline routes.
├── anime/        # domain logic: AniList-backed orchestration (Provider Protocol/ABC) — stub
├── anilist/       # AniList GraphQL client — stub
├── cache/          # in-memory cache (e.g. cachetools.TTLCache); Redis is a documented future upgrade, not v1 — stub
├── routers/        # FastAPI routers + request/response Pydantic models — stub
└── config.py       # pydantic-settings env/config loading — stub (currently just a TODO comment; env vars in .env.example aren't wired up yet)
```

### The API contract is `CONTRACT.md`, not the PRD

`CONTRACT.md` is copy-pasted verbatim into both this repo and the frontend repo (`kyomei_0`) and is the single source of truth for the HTTP boundary between them — **if an endpoint, field, or status code isn't listed there, it doesn't exist yet.** Propose contract changes via a PR to that file in both repos before implementing.

Note a naming inconsistency between docs: `CONTRACT.md` specifies paths under `/v1/...` (e.g. `GET /v1/anime/{malId}`), while the older checklist text and PRD reference `/api/...` paths. Treat `CONTRACT.md`'s `/v1/...` paths as authoritative when implementing routers.

**Any change to the HTTP API boundary — new/changed endpoints, request or response fields, status codes, or error shapes — must be reflected in `CONTRACT.md` in the same change.** `CONTRACT.md` is copy-pasted verbatim into the frontend repo (`kyomei_0`), so an update here without a matching update there (and vice versa) puts the two repos out of sync silently.

Current contract v1 scope (see `CONTRACT.md` for full detail):
- `GET /health` — liveness/readiness.
- `GET /v1/anime/{malId}` — single anime lookup via AniList, cached.
- `GET /v1/anime/search` — title search, same caching.
- `GET /v1/anime/{malId}/characters` — cast listing, same caching.
- All endpoints are public/unauthenticated in v1; JSON fields are `camelCase`; timestamps are Unix milliseconds.
- `POST /v1/recommendations` and watchlist endpoints are drafted under "Proposed / Not Yet Confirmed" — **do not implement these** until they're moved into the contract's "Endpoints" section.

### Why FastAPI, not Go

The repo originally started as a Go scaffold (`go mod init` only, no source). Per the PRD's "Design Decisions" section, the backend language was changed to Python/FastAPI because the core recommendation logic is a data-shaping/ranking problem better suited to Python's ecosystem, and FastAPI's async-native design plus Pydantic validation maps closely to the TypeScript interfaces already fixed in `CONTRACT.md`. The Go scaffold was retired (`go.mod` removed, `.gitignore` switched from Go- to Python-flavored) since there was no Go source to port.
