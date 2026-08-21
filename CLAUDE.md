# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Kyomei is a personalized anime recommendation app. This repo (`kyomei_api`, module `github.com/DavidRaet/kyomei-api`) is the **Go backend**. The frontend lives in a **separate repo** (`kyomei_0`, Vite + React + TypeScript) which currently fetches anime data client-side via `src/api/animeProvider.ts` (with `anilist.ts` as primary source, `jikan.ts` as fallback, `cache.ts` for client-side caching).

The current phase's goal is to stand up a Go service that sits behind `animeProvider.ts`, owning API orchestration (AniList primary + Jikan fallback) and shared caching — a server-side mirror of what the frontend already does client-side. Auth and personalization/recommendations are explicitly **out of scope for this phase** and covered by later, separate work.

## Current Repo State

This repo is a bare skeleton: `go.mod` (Go 1.26.3, no dependencies yet) plus a planning doc at `docs/go-backend-setup-checklist.md`. **No Go source files exist yet** — no `cmd/`, no `internal/`, no `main.go`. There is no Makefile, no CI, no Dockerfile, no tests.

There are no working build/test commands yet because there's no code to build or test. Once `cmd/api/main.go` and packages under `internal/` exist (per the architecture below), the standard Go commands apply:

- `go run ./cmd/api` — run the server locally
- `go build ./...` — build all packages
- `go test ./...` — run all tests; `go test ./internal/anime/...` to scope to one package
- `go vet ./...` — static analysis

Don't assume a Makefile, linter config, or CI pipeline exists — check before referencing one, since none are in the repo yet.

## Architecture — Near-Term (build this first)

Per `docs/go-backend-setup-checklist.md`, the intended layout organizes `internal/` by **domain**, not technical layer:

```
cmd/api/main.go          # wiring only — load config, start server; no business logic
internal/
  anime/                 # domain logic: Provider interface (GetByID, Search, GetCharacters), fallback orchestration
  anilist/                # AniList GraphQL client (mirrors frontend's anilist.ts)
  jikan/                  # Jikan REST client, fallback (mirrors frontend's jikan.ts)
  cache/                  # caching layer — start in-memory (sync.Map + TTL or simple LRU); Redis is a later upgrade, not required now
  transport/http/          # HTTP handlers, routing, middleware (CORS, request logging, per-IP rate limiting)
  config/                  # env/config loading
```

Design rules that apply to this phase:

- Keep `cmd/api/main.go` minimal — wiring only.
- Organize `internal/` by domain (`anime`, `anilist`, `jikan`, `cache`), not by technical layer (no generic `handlers`/`services`/`models` grab-bags).
- Match the frontend's existing provider/fallback pattern conceptually: try AniList, fall back to Jikan on error/timeout. This is a server-side mirror of `animeProvider.ts`, not a redesign.
- **Do not introduce a database, Redis, or auth in this phase.** Those are deferred to later, separate work (see below).
- Favor stdlib-first, idiomatic Go over heavy frameworks (`net/http` + a lightweight router if needed) — this project doubles as Go-learning practice, so prefer simplicity over batteries-included frameworks.
- Planned first endpoints: `GET /api/anime/:id`, `GET /api/anime/search`, `GET /api/anime/:id/characters`, plus `GET /healthz`.

## Architecture — Long-Term Vision (later phases, not started)

A separate PRD describes a much larger eventual scope for Kyomei, layered on top of this backend once the near-term BFF phase is solid: Auth0-based auth (JWT validated via Auth0's JWKS endpoint), a PostgreSQL database (`users`, `user_preferences`, `anime`, `user_ratings`, `user_watchlist`), a content-based recommendation engine (tag-matching + rating boost), a "vibe check" onboarding survey, ratings, and a watchlist — eventually with the Go server serving the compiled React frontend as a single deployable.

That PRD's proposed structure (`cmd/server`, `internal/auth`, `internal/handlers`, `internal/db`, `internal/recommendations`, `internal/models`) **differs from the near-term checklist's layout above** and assumes the frontend is folded into this repo rather than staying separate (`kyomei_0`). Treat the PRD as directional context for where the product is headed, not as the current architecture to build against — the checklist's domain-oriented layout and "no DB/auth yet" stance is what governs this phase. If/when auth or persistence work actually begins, expect the folder structure to be reconciled explicitly at that time rather than assumed from the PRD.

## Key External Dependency

The separate `kyomei_0` frontend repo and its `src/api/animeProvider.ts` abstraction are the consumer this service is built for. Keep client-facing endpoint shapes compatible with what that abstraction already expects from AniList/Jikan, since the intent is for the frontend to eventually call this backend instead of fetching directly.
