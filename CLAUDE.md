# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state of this repo

**Scaffolding, all five v1 anime endpoints, CORS, rate limiting, and request logging are done; caching is the one functional gap left.** `app/anime/` (models, errors, `Provider` protocol — now with `get_trending`/`get_seasonal` alongside `get_by_id`/`search`/`get_characters`), `app/anilist/client.py` (async AniList GraphQL client), `app/routers/` (the anime router, camelCase Pydantic schemas, exception handlers), `app/config.py` (`pydantic-settings`, wired into `app/main.py`), `app/rate_limit.py` (`slowapi`-based per-IP limiting), and `app/logging_config.py` (structured request logging middleware) are all implemented — `GET /health` plus five contract endpoints (`GET /v1/anime/{malId}`, `GET /v1/anime/search`, `GET /v1/anime/trending`, `GET /v1/anime/seasonal`, `GET /v1/anime/{malId}/characters`) work end-to-end against AniList, with CORS restricted to `app/config.py`'s `cors_allowed_origins` and every endpoint (including `/health`) rate-limited, returning `429`/`code: "rate_limited"` on breach. `app/cache/` is still an **empty stub module** (a one-line comment, nothing else): despite `CONTRACT.md` describing these responses as cached, every request currently hits AniList directly, and the `CACHE_TTL_SECONDS` setting in `app/config.py` isn't read by anything yet — same for `port` (Uvicorn binds `$PORT` directly; `Settings.port` is unused). There's also no separate orchestration layer (`app/anime/service.py`) — `AniListClient` implements the `Provider` protocol directly and is used as-is. A prior Go scaffold (`go.mod`, `go.sum`) was created and then deleted — see "Why FastAPI, not Go" below — so **do not re-introduce Go tooling** or assume any Go code exists to port.

This maps to `docs/fastapi-backend-setup-checklist.md`: Sections 1, 2, 3, 5, 6, 7, and 8 (repo/project structure, dependencies/tooling, core service implementation, testing, containerization, CI/CD, deploy) are now fully checked off, including a `pre-commit` hook (`.pre-commit-config.yaml`, installed via `just hooks-install`) that runs `ruff check`, `ruff format --check`, and `pytest` before each commit, mirroring CI. Section 4 (local dev verification) is also checked off. What's actually left: Section 9 (frontend cutover — `kyomei_0` needs to drop its AniList/Jikan client-side fallback once this backend is trusted) and Section 10 (docs — root `README.md` narrative sections, and a short architecture write-up for resume/interview purposes) are the open items; **caching (`app/cache/`) remains the biggest functional gap**, since `CONTRACT.md` already documents these endpoints as cached.

Before writing code, read, in this order:
1. `docs/fastapi-backend-setup-checklist.md` — the task list; check which items are still unchecked before assuming something is or isn't built.
2. `CONTRACT.md` — the authoritative HTTP contract with the frontend (`kyomei_0`).
3. `docs/Kyomei-MVP-PRD-v2.1.md` — full product context; most of it (auth, Postgres, recommendations) is **out of scope for this repo's current phase**, but explains where things are headed.

Follow the existing layout under `app/` (see "Architecture" below) rather than inventing a different structure — the module boundaries already exist, they just need implementations filled in.

When writing or debugging AniList GraphQL queries (in `app/anilist/client.py` or elsewhere), use the `anilist-graphql` skill rather than guessing at the schema.

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

`ruff` (`pyproject.toml`'s `[tool.ruff]`) enforces `E`, `F`, `I` (pyflakes/pycodestyle/import-sort) at a 120-char line length with double-quote formatting — match this style rather than an 80/100-char or single-quote convention.

Copy `.env.example` to `.env` before running locally (`PORT`, `ANILIST_ENDPOINT`, `CACHE_TTL_SECONDS`, `CORS_ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_ENABLED`). `PORT` and `CACHE_TTL_SECONDS` aren't read by any code yet; the rest are.

Run `just hooks-install` once per clone to enable the pre-commit hook (`ruff check`, `ruff format --check`, `pytest` before each commit); `just hooks-run` runs it on demand against all files.

Docker: `docker build -t kyomei-api .` / `docker run --rm -p 8000:8000 kyomei-api`. The image uses `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` and installs deps in a separate layer from app code before copying `app/` in, so editing source doesn't invalidate the dependency-install layer. `CMD` reads `$PORT` at runtime (Railway sets this in prod; falls back to 8000 locally) — this only works because it uses the shell form, not exec form.

CI (`.github/workflows/ci.yml`) runs two independent jobs on every PR and on push to `main`: `lint-and-test` (`uv sync`, `ruff check`, `pytest`) and `docker-build` (`docker build` only, no push). See `docs/learning/cicd-notes.md` and `docs/learning/docker-notes.md` for the reasoning behind these setups if you need to modify them.

## Architecture

**This is a BFF (backend-for-frontend), not the recommendation engine described in the PRD.** The PRD (`docs/Kyomei-MVP-PRD-v2.1.md`) describes a much larger eventual system (Auth0, PostgreSQL, ratings, watchlist, recommendations). That is explicitly **out of scope** for the current phase — this repo's job right now is orchestration + caching only, per `docs/fastapi-backend-setup-checklist.md`'s "Notes for Claude Code" section:

- Keep `app/main.py` wiring-only — no business logic.
- Organize real logic under `app/` by *domain* (`anime`, `anilist`, `cache`), not by technical layer.
- This service mirrors the frontend's provider abstraction server-side, not its fallback shape. The frontend (`kyomei_0`, a separate repo) has `src/api/animeProvider.ts` (abstraction point), `src/api/anilist.ts` (data source), and `src/api/cache.ts` (client-side cache). `kyomei_api` uses AniList as its sole upstream data source — a Jikan client was implemented and then removed as a fallback (see `docs/Kyomei-MVP-PRD-v2.1.md`'s Design Decisions for why); don't reintroduce a Jikan client without revisiting that decision.
- Don't add Redis, a database, or auth in this phase, even though the PRD describes them for later phases.
- Favor light async libraries (`httpx`, `cachetools`) over heavier frameworks/ORMs.

Module layout — `app/cache/` is still a docstring-only stub (read the one-line comment at the top of its `__init__.py`); everything else below is implemented:

```
app/
├── main.py             # FastAPI app creation, lifespan-managed AniListClient, CORS + rate-limit + logging middleware, router mounting, config load — wiring only. Defines GET /health inline; app/routers/anime.py is mounted for the /v1/anime/... endpoints.
├── anime/              # domain logic: models.py (AnimeSummary/AnimeDetail/CharacterSummary/VoiceActorSummary), errors.py (AnimeNotFoundError/UpstreamError), provider.py (Provider Protocol: get_by_id/search/get_characters/get_trending/get_seasonal) — implemented. No separate orchestration/service.py yet; AniListClient implements Provider directly.
├── anilist/            # client.py — async AniList GraphQL client (httpx), implements Provider structurally — implemented
├── cache/              # in-memory cache (e.g. cachetools.TTLCache); Redis is a documented future upgrade, not v1 — still a stub, not implemented
├── routers/            # anime.py (five /v1/anime endpoints) + schemas.py (camelCase Pydantic I/O models) + errors.py (exception handlers for 400/404/500) — implemented
├── rate_limit.py       # slowapi Limiter, per-IP, keyed on settings.rate_limit_per_minute/rate_limit_enabled; 429 responses shaped as ErrorResponse with code "rate_limited" — implemented
├── logging_config.py   # stdlib logging setup + a BaseHTTPMiddleware that logs method/path/status/duration/client IP per request — implemented
└── config.py           # pydantic-settings Settings (port, anilist_endpoint, cache_ttl_seconds, cors_allowed_origins, rate_limit_per_minute, rate_limit_enabled), loaded in main.py — implemented; anilist_endpoint feeds AniListClient, cors_allowed_origins feeds CORSMiddleware, rate_limit_* feed app/rate_limit.py; port and cache_ttl_seconds still aren't read anywhere
```

### The API contract is `CONTRACT.md`, not the PRD

`CONTRACT.md` is copy-pasted verbatim into both this repo and the frontend repo (`kyomei_0`) and is the single source of truth for the HTTP boundary between them — **if an endpoint, field, or status code isn't listed there, it doesn't exist yet.** Propose contract changes via a PR to that file in both repos before implementing.

Note a naming inconsistency between docs: `CONTRACT.md` specifies paths under `/v1/...` (e.g. `GET /v1/anime/{malId}`), while the older checklist text and PRD reference `/api/...` paths. Treat `CONTRACT.md`'s `/v1/...` paths as authoritative when implementing routers.

**Any change to the HTTP API boundary — new/changed endpoints, request or response fields, status codes, or error shapes — must be reflected in `CONTRACT.md` in the same change.** `CONTRACT.md` is copy-pasted verbatim into the frontend repo (`kyomei_0`), so an update here without a matching update there (and vice versa) puts the two repos out of sync silently.

Current contract v1 scope (see `CONTRACT.md`'s Endpoints section for full detail — its earlier sections have unresolved merge-conflict markers, see above):
- `GET /health` — liveness/readiness.
- `GET /v1/anime/{malId}` — single anime lookup via AniList, contract-documented as cached (not actually cached yet — see above).
- `GET /v1/anime/search` — title search, same caching note.
- `GET /v1/anime/trending` — currently-trending anime via AniList.
- `GET /v1/anime/seasonal` — anime for a given season/year via AniList.
- `GET /v1/anime/{malId}/characters` — cast listing, same caching note.
- All endpoints — including `/health` — are rate-limited per client IP; a breach returns `429` with `code: "rate_limited"`.
- All endpoints are public/unauthenticated in v1; JSON fields are `camelCase`; timestamps are Unix milliseconds.
- `POST /v1/recommendations` and watchlist endpoints are drafted under "Proposed / Not Yet Confirmed" — **do not implement these** until they're moved into the contract's "Endpoints" section.

### Why FastAPI, not Go

The repo originally started as a Go scaffold (`go mod init` only, no source). Per the PRD's "Design Decisions" section, the backend language was changed to Python/FastAPI because the core recommendation logic is a data-shaping/ranking problem better suited to Python's ecosystem, and FastAPI's async-native design plus Pydantic validation maps closely to the TypeScript interfaces already fixed in `CONTRACT.md`. The Go scaffold was retired (`go.mod` removed, `.gitignore` switched from Go- to Python-flavored) since there was no Go source to port.