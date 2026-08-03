# Kyomei: Go Backend Setup Checklist (Init → Deploy)

## Context

The frontend (`kyomei_0`, Vite + React + TypeScript) has already migrated its primary anime data source from Jikan to AniList GraphQL, with `src/api/animeProvider.ts` as the single abstraction point components call into, `src/api/anilist.ts` as primary, `src/api/jikan.ts` as fallback, and `src/api/cache.ts` for client-side caching.

**Goal of this phase:** stand up a new Go backend service that will eventually sit behind `animeProvider.ts`, owning API orchestration (AniList + Jikan fallback), shared caching, and — later — personalization/recommendation logic tied to user accounts. This checklist covers only setup: scaffolding, local dev, and first deployment. It does not cover recommendation logic or auth (separate docs later).

This is a skeleton — check items off as completed, and expand any section into its own doc if it grows too large for Claude Code to hold in one pass.

---

## 1. Repo & Project Structure

- [X] Create a separate repo for clean deploy boundaries.
- [ ] Initialize Go module: `go mod init github.com/DavidRaet/kyomei-api` (or appropriate path)
- [ ] Scaffold standard layout:
  ```
  kyomei-api/
  ├── cmd/
  │   └── api/
  │       └── main.go          # wiring only — load config, start server
  ├── internal/
  │   ├── anime/                # domain logic: orchestration, fallback
  │   ├── anilist/               # AniList GraphQL client
  │   ├── jikan/                 # Jikan REST client (fallback)
  │   ├── cache/                 # caching layer (in-memory or Redis)
  │   ├── transport/
  │   │   └── http/              # HTTP handlers, routing, middleware
  │   └── config/                 # env/config loading
  ├── pkg/                        # only if code is meant to be externally reusable
  ├── api/
  │   └── openapi.yaml            # optional: API contract doc
  ├── scripts/
  │   └── deploy.sh
  ├── .env.example
  ├── go.mod
  ├── go.sum
  ├── Dockerfile
  └── README.md
  ```
- [ ] Add `.gitignore` (Go template + `.env`)
- [ ] Add root `README.md` with project purpose, local run instructions

## 2. Dependencies & Tooling

- [ ] Choose HTTP router/framework: `net/http` + `chi` (lightweight, idiomatic) or `gin`/`fiber` (more batteries-included) — pick one and document why in README
- [ ] Choose HTTP client for outbound calls (AniList/Jikan): standard `net/http` client with timeout config is sufficient
- [ ] Add config loading (e.g., `godotenv` for local `.env`, plain `os.Getenv` in prod)
- [ ] Add structured logging (`log/slog` from stdlib is sufficient for this project size)
- [ ] Set up `golangci-lint` config for consistent linting
- [ ] Add `Makefile` or `justfile` with common commands: `run`, `build`, `test`, `lint`

## 3. Core Service Implementation (Skeleton Only)

- [ ] Define domain interfaces first in `internal/anime/` (e.g., `Provider` interface with `GetByID`, `Search`, `GetCharacters`) — mirrors the frontend's `animeProvider.ts` pattern
- [ ] Implement `internal/anilist/client.go` — GraphQL client, queries mirroring what `src/api/anilist.ts` already does
- [ ] Implement `internal/jikan/client.go` — REST client, ported from `src/api/jikan.ts` fallback logic
- [ ] Implement fallback orchestration in `internal/anime/service.go`: try AniList, fall back to Jikan on error/timeout (use goroutines + `context.WithTimeout` for concurrent attempts if applicable)
- [ ] Implement `internal/cache/` — start with in-memory (`sync.Map` + TTL) or a simple LRU; note Redis as a documented upgrade path, not required for v1
- [ ] Implement HTTP handlers in `internal/transport/http/`: `GET /api/anime/:id`, `GET /api/anime/search`, `GET /api/anime/:id/characters`
- [ ] Add CORS middleware scoped to the frontend's dev/prod origins
- [ ] Add request logging + basic rate limiting middleware (per-IP)

## 4. Local Development

- [ ] `.env.example` with required vars (e.g., `PORT`, `ANILIST_ENDPOINT`, `JIKAN_BASE_URL`, `CACHE_TTL_SECONDS`)
- [ ] Verify `go run ./cmd/api` starts server locally on expected port
- [ ] Manually test each endpoint with `curl` or Postman against local server
- [ ] Point frontend's `animeProvider.ts` at `http://localhost:<port>/api/...` behind a feature flag or env var, without removing direct-fetch fallback yet

## 5. Testing

- [ ] Unit tests for `internal/anilist/` and `internal/jikan/` clients (mock HTTP responses)
- [ ] Unit tests for fallback orchestration logic in `internal/anime/service.go` (simulate AniList failure → confirm Jikan fallback triggers)
- [ ] Basic integration test hitting a running local server for one endpoint
- [ ] Add `go test ./...` to a pre-commit hook or CI step

## 6. Containerization

- [ ] Write multi-stage `Dockerfile` (build stage with `golang:alpine`, final stage with minimal scratch/alpine image)
- [ ] Verify `docker build` and `docker run` work locally, hitting the same endpoints as `go run`
- [ ] Add `.dockerignore`

## 7. CI/CD

- [ ] Add GitHub Actions workflow: run `go vet`, `golangci-lint`, `go test ./...` on every PR
- [ ] Add build step to confirm Docker image builds successfully in CI
- [ ] (Later) Add auto-deploy step once hosting platform is chosen (Section 8)

## 8. Deployment

- [ ] Choose hosting platform — options to evaluate:
  - **Fly.io**: good for Go binaries/Docker, generous free tier, simple `flyctl deploy`
  - **Render**: simple Docker/native Go deploys, good free tier for small services
  - Avoid Vercel for the Go service itself (Vercel is better suited to the frontend; it's not a natural fit for long-running Go HTTP servers)
- [ ] Set environment variables/secrets on the hosting platform (mirror `.env.example`)
- [ ] Deploy and verify health-check endpoint (`GET /healthz`) responds correctly in prod
- [ ] Point a subdomain or path (e.g., `api.kyomei.app`) at the deployed service, if using a custom domain
- [ ] Update frontend's production env var to point at deployed backend URL

## 9. Cutover from Client-Side Fetching

- [ ] Update `animeProvider.ts` to call the Go backend as primary, with existing client-side AniList/Jikan calls kept as an emergency fallback (temporary safety net)
- [ ] Monitor for a period (manually or via logs) to confirm backend reliability before removing client-side fallback entirely
- [ ] Once confident, simplify `animeProvider.ts` to call only the backend; remove now-redundant client-side caching/fallback logic from `src/api/cache.ts` and `src/api/jikan.ts` (or archive them for reference)

## 10. Documentation

- [ ] Update root `README.md` (frontend repo) to note the backend dependency and link to `kyomei-api` repo
- [ ] Document API contract (endpoints, request/response shapes) — OpenAPI spec optional but nice for portfolio presentation
- [ ] Write a short architecture note (can be a section in this doc or separate) explaining the BFF pattern used, for resume/interview talk-track purposes

---

## Notes for Claude Code

- Keep `cmd/api/main.go` minimal — wiring only, no business logic.
- Put all real logic under `internal/`, organized by domain (`anime`, `anilist`, `jikan`, `cache`), not by technical layer.
- Match the frontend's existing provider/fallback pattern conceptually — the Go service is a server-side mirror of what `animeProvider.ts` already does, not a redesign.
- Don't introduce Redis, a database, or auth in this pass — this checklist is setup-to-first-deploy only. Personalization, saved preferences, and auth are separate future docs.
- Favor flat package structure and idiomatic Go (stdlib-first) over heavy frameworks, given this is also a learning project for Go specialization.
