# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of this repo

**No application code exists yet.** This repo currently contains only planning docs (`README.md`, `CONTRACT.md`, `docs/`) and a local `.venv`. There is no `pyproject.toml`, no `app/` directory, no source files. A prior Go scaffold (`go.mod`, `go.sum`) was created and then deleted — see "Why FastAPI, not Go" below — so **do not re-introduce Go tooling** or assume any Go code exists to port.

Before writing code, read, in this order:
1. `docs/fastapi-backend-setup-checklist.md` — the actual task list for this phase (setup → first deploy only; no recommendations logic, no auth, no DB yet).
2. `CONTRACT.md` — the authoritative HTTP contract with the frontend (`kyomei_0`).
3. `docs/Kyomei-MVP-PRD-v2.1.md` — full product context; most of it (auth, Postgres, recommendations) is **out of scope for this repo's current phase**, but explains where things are headed.

When scaffolding, follow the checklist's proposed layout under `app/` (see "Architecture" below) rather than inventing a different structure.

## Commands

No dependency manager or test runner is set up yet. Per the checklist, this project uses **`uv`** (not poetry/pip directly). Once scaffolded, the intended commands are:

```
uv sync                              # install dependencies
uv run uvicorn app.main:app --reload # run the dev server
uv run pytest                        # run all tests
uv run pytest tests/path/to_test.py::test_name   # run a single test
uv run ruff check                    # lint
uv run ruff format                   # format
```

If a `Makefile`/`justfile` gets added later (checklist item), prefer its targets over calling `uv run ...` directly, and update this section to match.

## Architecture

**This is a BFF (backend-for-frontend), not the recommendation engine described in the PRD.** The PRD (`docs/Kyomei-MVP-PRD-v2.1.md`) describes a much larger eventual system (Auth0, PostgreSQL, ratings, watchlist, recommendations). That is explicitly **out of scope** for the current phase — this repo's job right now is orchestration + caching only, per `docs/fastapi-backend-setup-checklist.md`'s "Notes for Claude Code" section:

- Keep `app/main.py` wiring-only — no business logic.
- Organize real logic under `app/` by *domain* (`anime`, `anilist`, `jikan`, `cache`), not by technical layer.
- This service mirrors the frontend's existing provider/fallback pattern server-side — it is not a redesign. The frontend (`kyomei_0`, a separate repo) already has `src/api/animeProvider.ts` (abstraction point), `src/api/anilist.ts` (primary source), `src/api/jikan.ts` (fallback), and `src/api/cache.ts` (client-side cache). This backend is meant to be a server-side equivalent of that same AniList-primary/Jikan-fallback shape.
- Don't add Redis, a database, or auth in this phase, even though the PRD describes them for later phases.
- Favor light async libraries (`httpx`, `cachetools`) over heavier frameworks/ORMs.

Planned module layout (from the checklist):

```
app/
├── main.py       # FastAPI app creation, router mounting, config load — wiring only
├── anime/        # domain logic: orchestration + AniList→Jikan fallback (Provider Protocol/ABC)
├── anilist/       # AniList GraphQL client
├── jikan/          # Jikan REST client (fallback only)
├── cache/          # in-memory cache (e.g. cachetools.TTLCache); Redis is a documented future upgrade, not v1
├── routers/        # FastAPI routers + request/response Pydantic models
└── config.py       # pydantic-settings env/config loading
```

### The API contract is `CONTRACT.md`, not the PRD

`CONTRACT.md` is copy-pasted verbatim into both this repo and the frontend repo (`kyomei_0`) and is the single source of truth for the HTTP boundary between them — **if an endpoint, field, or status code isn't listed there, it doesn't exist yet.** Propose contract changes via a PR to that file in both repos before implementing.

Note a naming inconsistency between docs: `CONTRACT.md` specifies paths under `/v1/...` (e.g. `GET /v1/anime/{malId}`), while the older checklist text and PRD reference `/api/...` paths. Treat `CONTRACT.md`'s `/v1/...` paths as authoritative when implementing routers.

**Any change to the HTTP API boundary — new/changed endpoints, request or response fields, status codes, or error shapes — must be reflected in `CONTRACT.md` in the same change.** `CONTRACT.md` is copy-pasted verbatim into the frontend repo (`kyomei_0`), so an update here without a matching update there (and vice versa) puts the two repos out of sync silently.

Current contract v1 scope (see `CONTRACT.md` for full detail):
- `GET /health` — liveness/readiness.
- `GET /v1/anime/{malId}` — single anime lookup, AniList primary → Jikan fallback, cached.
- `GET /v1/anime/search` — title search, same fallback/caching.
- `GET /v1/anime/{malId}/characters` — cast listing, same fallback/caching.
- All endpoints are public/unauthenticated in v1; JSON fields are `camelCase`; timestamps are Unix milliseconds.
- `POST /v1/recommendations` and watchlist endpoints are drafted under "Proposed / Not Yet Confirmed" — **do not implement these** until they're moved into the contract's "Endpoints" section.

### Why FastAPI, not Go

The repo originally started as a Go scaffold (`go mod init` only, no source). Per the PRD's "Design Decisions" section, the backend language was changed to Python/FastAPI because the core recommendation logic is a data-shaping/ranking problem better suited to Python's ecosystem, and FastAPI's async-native design plus Pydantic validation maps closely to the TypeScript interfaces already fixed in `CONTRACT.md`. The Go scaffold was retired (`go.mod` removed, `.gitignore` switched from Go- to Python-flavored) since there was no Go source to port.
