# Kyomei: FastAPI Backend Setup Checklist (Init → Deploy)

## Context

The frontend (`kyomei_0`, Vite + React + TypeScript) has already migrated its primary anime data source from Jikan to AniList GraphQL, with `src/api/animeProvider.ts` as the single abstraction point components call into, `src/api/anilist.ts` as primary, `src/api/jikan.ts` as fallback, and `src/api/cache.ts` for client-side caching.

**Goal of this phase:** stand up a new FastAPI (Python) backend service that will eventually sit behind `animeProvider.ts`, owning API orchestration (AniList), shared caching, and — later — personalization/recommendation logic tied to user accounts. This checklist covers only setup: scaffolding, local dev, and first deployment. It does not cover recommendation logic or auth (separate docs later).

This replaces `go-backend-setup-checklist.md` — per the PRD's "Design Decisions" section (`docs/Kyomei-MVP-PRD-v2.1.md`), the backend language changed from Go to Python/FastAPI. The Go scaffold in this repo was never more than `go mod init` (no source files), so there's nothing to port — only to retire. The scope of *this* checklist stays the same as the original: BFF-style orchestration and caching only. Auth0, PostgreSQL, Alembic, and the recommendation/ratings/watchlist endpoints described elsewhere in the PRD are intentionally out of scope here and belong in separate future docs.

This is a skeleton — check items off as completed, and expand any section into its own doc if it grows too large for Claude Code to hold in one pass.

---

## 1. Repo & Project Structure

- [X] Create a separate repo for clean deploy boundaries.
- [X] Retire the dead Go scaffold: remove `go.mod` (and `go.sum` if present) — no Go source files exist, so there's nothing to preserve
- [X] Replace the Go-flavored `.gitignore` with a Python one (`__pycache__/`, `*.pyc`, `.venv/`, `.env`, `.pytest_cache/`, `dist/`, `*.egg-info/`)
- [X] Initialize Python project: `uv init` (reason for favoring uv over poetry will be explained in the README)
- [X] Scaffold standard layout:
  ```
  kyomei-api/
  ├── app/
  │   ├── main.py                # wiring only — load config, create FastAPI app, mount routers
  │   ├── anime/                  # domain logic: orchestration
  │   ├── anilist/                 # AniList GraphQL client
  │   ├── cache/                   # caching layer (in-memory or Redis)
  │   ├── routers/                 # FastAPI routers, request/response models
  │   └── config.py                # env/config loading (pydantic-settings)
  ├── tests/
  ├── api/
  │   └── openapi.yaml             # optional: hand-written contract doc (FastAPI also auto-generates one)
  ├── scripts/
  │   └── deploy.sh
  ├── .env.example
  ├── pyproject.toml
  ├── Dockerfile
  └── README.md
  ```
- [X] Add root `README.md` with project purpose, local run instructions

## 2. Dependencies & Tooling

- [X] FastAPI + Uvicorn (ASGI) — async-native, Pydantic validation, and auto-generated OpenAPI docs (`/docs`, `/openapi.json`) come for free; document this choice in README
- [X] Choose HTTP client for outbound calls (AniList): `httpx` (async client with timeout config) is sufficient
- [X] Add config loading (`pydantic-settings` for typed env vars, or plain `python-dotenv` for local `.env`)
- [X] Add structured logging (stdlib `logging`, configured once at startup, is sufficient for this project size)
- [X] Set up `ruff` config for linting + formatting
- [X] Add `Makefile` or `justfile` with common commands: `run`, `test`, `lint`

## 3. Core Service Implementation 

- [X] Define domain interfaces first in `app/anime/` (e.g. a `Provider` `Protocol`/ABC with `get_by_id`, `search`, `get_characters`) — mirrors the frontend's `animeProvider.ts` pattern
- [X] Implement `app/anilist/client.py` — async GraphQL client (`httpx`), queries mirroring what `src/api/anilist.ts` already does
- [X] ~~Implement `app/jikan/client.py`~~ — implemented, then removed. Jikan was dropped as the fallback data source (unreliable scraper/wrapper around MyAnimeList, counterproductive as a fallback); AniList is now the sole upstream source — see `docs/Kyomei-MVP-PRD-v2.1.md`'s Design Decisions
- [X] Implement FastAPI routers in `app/routers/`: `GET /api/anime/{id}`, `GET /api/anime/search`, `GET /api/anime/{id}/characters`, `GET /api/anime/trending`, `GET /api/anime/seasonal`
- [X] Add CORS middleware (`fastapi.middleware.cors.CORSMiddleware`) scoped to the frontend's dev/prod origins
- [X] Add request logging + basic rate limiting middleware (per-IP — e.g. `slowapi`)

## 4. Local Development

- [x] `.env.example` with required vars (e.g. `PORT`, `ANILIST_ENDPOINT`, `CACHE_TTL_SECONDS`)
- [x] Verify `uvicorn app.main:app --reload` starts server locally on expected port
- [x] Manually test each endpoint via FastAPI's auto-generated Swagger UI (`/docs`) or `curl`/Postman
- [X] Point frontend's `animeProvider.ts` at `http://localhost:<port>/api/...` behind a feature flag or env var, without removing direct-fetch fallback yet

## 5. Testing

- [X] Unit tests for the `app/anilist/` client (mock HTTP responses with `pytest-httpx` or `respx`)
- [X] Unit tests for orchestration logic in `app/anime/service.py` (simulate AniList failure → confirm it surfaces as an `UpstreamError`/5xx, since there is no fallback source)
- [X] Basic integration test hitting a running local server for one endpoint (`httpx.AsyncClient`)
- [X] Add `pytest` to a pre-commit hook (`.pre-commit-config.yaml`; also runs `ruff check` / `ruff format --check`, mirroring CI)

## 6. Containerization

- [X] Write `Dockerfile` (`python:slim` base; multi-stage optional if compiling any deps)
- [X] Verify `docker build` and `docker run` work locally, hitting the same endpoints as `uvicorn`
- [X] Add `.dockerignore`

## 7. CI/CD

- [X] Add GitHub Actions workflow: run `ruff check`, `pytest` on every PR
- [X] Add build step to confirm Docker image builds successfully in CI
- [X] (Later) Add auto-deploy step once hosting platform is confirmed (Section 8)

## 8. Deployment

- [X] Deploy to **Railway** — the PRD already fixes this as the hosting platform (it will also host PostgreSQL once that lands in a later pass), so no platform evaluation needed here
- [X] Set environment variables/secrets on Railway (mirror `.env.example`)
- [X] Deploy and verify health-check endpoint (`GET /healthz`) responds correctly in prod
- [X] Update frontend's production env var to point at deployed backend URL

## 9. Cutover from Client-Side Fetching

- [ ] Monitor for a period (manually or via logs) to confirm backend reliability before removing client-side fallback entirely
- [ ] Once confident, simplify `animeProvider.ts` to call only the backend; remove now-redundant client-side caching/fallback logic from `src/api/cache.ts` and `src/api/jikan.ts` (or archive them for reference)

## 10. Documentation

- [ ] Update root `README.md` (frontend repo) to note the backend dependency and link to `kyomei-api` repo
- [ ] Document the API contract: `CONTRACT.md` is referenced by the PRD as if it already exists, but it does not — either create it for real here, or explicitly treat FastAPI's auto-generated OpenAPI docs (`/docs`, `/openapi.json`) as the interim source of truth until it's written
- [ ] Write a short architecture note (can be a section in this doc or separate) explaining the BFF pattern used, and linking to the PRD's "Design Decisions" section for the Go → FastAPI rationale, for resume/interview talk-track purposes

---

## Notes for Claude Code

- Keep `app/main.py` minimal — wiring only, no business logic.
- Put all real logic under `app/`, organized by domain (`anime`, `anilist`, `cache`), not by technical layer.
- Match the frontend's provider abstraction conceptually — the FastAPI service mirrors what `animeProvider.ts`'s abstraction point does, not its fallback shape. `kyomei_api` uses AniList as its sole upstream data source; it does not implement a Jikan fallback (a Jikan client was built and then removed — see `docs/Kyomei-MVP-PRD-v2.1.md`'s Design Decisions for why).
- Don't introduce Redis, a database, or auth in this pass — this checklist is setup-to-first-deploy only. Personalization, saved preferences, Auth0, and PostgreSQL are separate future docs, even though the PRD's full technical architecture describes them as part of the eventual backend.
- Favor async-first, lightweight libraries (`httpx`, `cachetools`) over heavyweight frameworks — FastAPI + Pydantic already provide structure, so avoid layering on more than this service needs.
