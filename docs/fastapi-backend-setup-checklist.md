# Kyomei: FastAPI Backend Setup Checklist (Init → Deploy)

## Context

The frontend (`kyomei_0`, Vite + React + TypeScript) has already migrated its primary anime data source from Jikan to AniList GraphQL, with `src/api/animeProvider.ts` as the single abstraction point components call into, `src/api/anilist.ts` as primary, `src/api/jikan.ts` as fallback, and `src/api/cache.ts` for client-side caching.

**Goal of this phase:** stand up a new FastAPI (Python) backend service that will eventually sit behind `animeProvider.ts`, owning API orchestration (AniList + Jikan fallback), shared caching, and — later — personalization/recommendation logic tied to user accounts. This checklist covers only setup: scaffolding, local dev, and first deployment. It does not cover recommendation logic or auth (separate docs later).

This replaces `go-backend-setup-checklist.md` — per the PRD's "Design Decisions" section (`docs/Kyomei-MVP-PRD-v2.1.md`), the backend language changed from Go to Python/FastAPI. The Go scaffold in this repo was never more than `go mod init` (no source files), so there's nothing to port — only to retire. The scope of *this* checklist stays the same as the original: BFF-style orchestration and caching only. Auth0, PostgreSQL, Alembic, and the recommendation/ratings/watchlist endpoints described elsewhere in the PRD are intentionally out of scope here and belong in separate future docs.

This is a skeleton — check items off as completed, and expand any section into its own doc if it grows too large for Claude Code to hold in one pass.

---

## 1. Repo & Project Structure

- [X] Create a separate repo for clean deploy boundaries.
- [ ] Retire the dead Go scaffold: remove `go.mod` (and `go.sum` if present) — no Go source files exist, so there's nothing to preserve
- [ ] Replace the Go-flavored `.gitignore` with a Python one (`__pycache__/`, `*.pyc`, `.venv/`, `.env`, `.pytest_cache/`, `dist/`, `*.egg-info/`)
- [ ] Initialize Python project: `uv init` (reason for favoring uv over poetry will be explained in the README)
- [ ] Scaffold standard layout:
  ```
  kyomei-api/
  ├── app/
  │   ├── main.py                # wiring only — load config, create FastAPI app, mount routers
  │   ├── anime/                  # domain logic: orchestration, fallback
  │   ├── anilist/                 # AniList GraphQL client
  │   ├── jikan/                   # Jikan REST client (fallback)
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
- [ ] Add root `README.md` with project purpose, local run instructions

## 2. Dependencies & Tooling

- [ ] FastAPI + Uvicorn (ASGI) — async-native, Pydantic validation, and auto-generated OpenAPI docs (`/docs`, `/openapi.json`) come for free; document this choice in README
- [ ] Choose HTTP client for outbound calls (AniList/Jikan): `httpx` (async client with timeout config) is sufficient
- [ ] Add config loading (`pydantic-settings` for typed env vars, or plain `python-dotenv` for local `.env`)
- [ ] Add structured logging (stdlib `logging`, configured once at startup, is sufficient for this project size)
- [ ] Set up `ruff` config for linting + formatting
- [ ] Add `Makefile` or `justfile` with common commands: `run`, `test`, `lint`

## 3. Core Service Implementation (Skeleton Only)

- [ ] Define domain interfaces first in `app/anime/` (e.g. a `Provider` `Protocol`/ABC with `get_by_id`, `search`, `get_characters`) — mirrors the frontend's `animeProvider.ts` pattern
- [ ] Implement `app/anilist/client.py` — async GraphQL client (`httpx`), queries mirroring what `src/api/anilist.ts` already does
- [ ] Implement `app/jikan/client.py` — async REST client (`httpx`), ported from `src/api/jikan.ts` fallback logic
- [ ] Implement fallback orchestration in `app/anime/service.py`: try AniList, fall back to Jikan on error/timeout (`httpx` timeouts + `try/except`; use `asyncio.wait_for`/`asyncio.gather` if concurrent attempts are wanted)
- [ ] Implement `app/cache/` — start with in-memory (`cachetools.TTLCache` or a plain dict + expiry) or a simple LRU; note Redis as a documented upgrade path, not required for v1
- [ ] Implement FastAPI routers in `app/routers/`: `GET /api/anime/{id}`, `GET /api/anime/search`, `GET /api/anime/{id}/characters`
- [ ] Add CORS middleware (`fastapi.middleware.cors.CORSMiddleware`) scoped to the frontend's dev/prod origins
- [ ] Add request logging + basic rate limiting middleware (per-IP — e.g. `slowapi`)

## 4. Local Development

- [ ] `.env.example` with required vars (e.g. `PORT`, `ANILIST_ENDPOINT`, `JIKAN_BASE_URL`, `CACHE_TTL_SECONDS`)
- [ ] Verify `uvicorn app.main:app --reload` starts server locally on expected port
- [ ] Manually test each endpoint via FastAPI's auto-generated Swagger UI (`/docs`) or `curl`/Postman
- [ ] Point frontend's `animeProvider.ts` at `http://localhost:<port>/api/...` behind a feature flag or env var, without removing direct-fetch fallback yet

## 5. Testing

- [ ] Unit tests for `app/anilist/` and `app/jikan/` clients (mock HTTP responses with `pytest-httpx` or `respx`)
- [ ] Unit tests for fallback orchestration logic in `app/anime/service.py` (simulate AniList failure → confirm Jikan fallback triggers)
- [ ] Basic integration test hitting a running local server for one endpoint (`httpx.AsyncClient` or FastAPI `TestClient`)
- [ ] Add `pytest` to a pre-commit hook or CI step

## 6. Containerization

- [ ] Write `Dockerfile` (`python:slim` base; multi-stage optional if compiling any deps)
- [ ] Verify `docker build` and `docker run` work locally, hitting the same endpoints as `uvicorn`
- [ ] Add `.dockerignore`

## 7. CI/CD

- [ ] Add GitHub Actions workflow: run `ruff check`, `pytest` on every PR
- [ ] Add build step to confirm Docker image builds successfully in CI
- [ ] (Later) Add auto-deploy step once hosting platform is confirmed (Section 8)

## 8. Deployment

- [ ] Deploy to **Railway** — the PRD already fixes this as the hosting platform (it will also host PostgreSQL once that lands in a later pass), so no platform evaluation needed here
- [ ] Set environment variables/secrets on Railway (mirror `.env.example`)
- [ ] Deploy and verify health-check endpoint (`GET /healthz`) responds correctly in prod
- [ ] Point a subdomain or path (e.g. `api.kyomei.app`) at the deployed service, if using a custom domain
- [ ] Update frontend's production env var to point at deployed backend URL

## 9. Cutover from Client-Side Fetching

- [ ] Update `animeProvider.ts` to call the FastAPI backend as primary, with existing client-side AniList/Jikan calls kept as an emergency fallback (temporary safety net)
- [ ] Monitor for a period (manually or via logs) to confirm backend reliability before removing client-side fallback entirely
- [ ] Once confident, simplify `animeProvider.ts` to call only the backend; remove now-redundant client-side caching/fallback logic from `src/api/cache.ts` and `src/api/jikan.ts` (or archive them for reference)

## 10. Documentation

- [ ] Update root `README.md` (frontend repo) to note the backend dependency and link to `kyomei-api` repo
- [ ] Document the API contract: `CONTRACT.md` is referenced by the PRD as if it already exists, but it does not — either create it for real here, or explicitly treat FastAPI's auto-generated OpenAPI docs (`/docs`, `/openapi.json`) as the interim source of truth until it's written
- [ ] Write a short architecture note (can be a section in this doc or separate) explaining the BFF pattern used, and linking to the PRD's "Design Decisions" section for the Go → FastAPI rationale, for resume/interview talk-track purposes

---

## Notes for Claude Code

- Keep `app/main.py` minimal — wiring only, no business logic.
- Put all real logic under `app/`, organized by domain (`anime`, `anilist`, `jikan`, `cache`), not by technical layer.
- Match the frontend's existing provider/fallback pattern conceptually — the FastAPI service is a server-side mirror of what `animeProvider.ts` already does, not a redesign.
- Don't introduce Redis, a database, or auth in this pass — this checklist is setup-to-first-deploy only. Personalization, saved preferences, Auth0, and PostgreSQL are separate future docs, even though the PRD's full technical architecture describes them as part of the eventual backend.
- Favor async-first, lightweight libraries (`httpx`, `cachetools`) over heavyweight frameworks — FastAPI + Pydantic already provide structure, so avoid layering on more than this service needs.
