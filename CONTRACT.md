# Kyomei API Contract

**Last updated:** 2026-08-13

This document is the single source of truth for the HTTP API boundary between:

- **`kyomei_api`** — FastAPI backend service, owns AniList/Jikan orchestration + caching now, and (eventually) recommendation logic and any server-side user state.
- **`kyomei_0`** — TypeScript/Vite frontend, migrating anime metadata/browsing calls from direct AniList/Jikan access to `kyomei_api`, and will call it for personalized recommendations once that phase lands.

This file is copy-pasted verbatim into both repositories. Neither side needs to read the other's source code — only this contract. If an endpoint, field, or status code isn't listed here, it doesn't exist yet. Propose changes via a PR to this file in both repos before implementing.

## Scope

Per `docs/fastapi-backend-setup-checklist.md`, `kyomei_api` v1 is a BFF-style orchestration layer, not a recommendation service yet — that lands in a later phase once personalization/auth work begins.

**In scope for `kyomei_api` (v1):**
- Anime lookup, search, and character listing, orchestrated server-side: AniList primary, Jikan fallback on error/timeout — a server-side mirror of what `animeProvider.ts` already does client-side.
- Shared caching of the above (in-memory for v1; Redis is a documented future upgrade, not required now).
- Basic service health reporting.

**Explicitly out of scope for `kyomei_api` (v1):**
- Turning a user's watch history into a ranked recommendation list, and any other personalization logic. This was previously drafted as in-scope but has not been implemented — see `POST /v1/recommendations` under "Proposed / Not Yet Confirmed" below.
- Authentication (Auth0) — all endpoints are public/unauthenticated in v1 (see Auth section).
- Any persistent server-side storage — PostgreSQL, Alembic migrations, watchlists, or user accounts. `kyomei_0` currently owns watchlist state locally (see `WatchlistEntry`). If/when this moves server-side, it will be added to this contract as a new versioned endpoint — see "Proposed / Not Yet Confirmed" below.

## Conventions

- Base path: all endpoints are prefixed with `/v1` except the health check.
- All request/response bodies are `application/json`.
- Field names in JSON bodies are `camelCase`. 
- Timestamps are Unix milliseconds (`number`), matching `WatchlistEntry.addedAt` convention already used in `kyomei_0`.
- No endpoint requires authentication in v1 (see Auth section).

## Shared Types

These types are the common vocabulary for every endpoint below.

```typescript
// Canonical normalized anime shape returned by kyomei_api.
// Mirrors the frontend's existing `Anime` type (src/types/types.ts) so no
// mapping layer is needed on the kyomei_0 side.
interface AnimeSummary {
  malId: number;
  titleEnglish: string;
  titleJp?: string;
  image: string;
  score: number | null;
  episodes: number | null;
  year: number | null;
  season: string | null;
  status: string;
  format: string;
  genres: string[];
  studios: string[];
}

// Response shape for GET /v1/anime/search.
interface AnimeSearchResponse {
  data: AnimeSummary[];
  total?: number; // optional, only if the upstream source reports a total count
}

// A single cast member returned by GET /v1/anime/{malId}/characters.
// Field shapes are provisional — kyomei_0's character rendering needs weren't
// available to cross-check from this repo; adjust if they don't match once wired up.
interface CharacterSummary {
  malId: number;
  name: string;
  image: string;
  role: string; // e.g. "Main", "Supporting"
}

// Matches the frontend's WatchlistStatus (src/types/watchlist.ts).
// Only consumed by POST /v1/recommendations, which is currently Proposed, not live — see below.
type WatchlistStatus = 'watching' | 'completed' | 'planning';

// A single history entry the client sends to describe what the user has watched.
// Only consumed by POST /v1/recommendations, which is currently Proposed, not live — see below.
interface HistoryEntry {
  malId: number;
  status: WatchlistStatus;
  score?: number; // user's personal rating, 1-10, if they gave one
}

// Uniform error body for any non-2xx response from any endpoint.
interface ErrorResponse {
  error: {
    code: string;    // machine-readable, e.g. "invalid_request", "not_found", "internal_error"
    message: string; // human-readable, safe to display in logs or minimal UI
  };
}
```

## Endpoints

### `GET /health`

Liveness/readiness probe for deployment and local dev sanity checks. No path/query params, no body, no auth.

**Response — success**

```typescript
interface HealthResponse {
  status: 'ok';
}
```

- `200 OK` — service is up, body as above.
- `503 Service Unavailable` — service is degraded/not ready, body as `ErrorResponse` with `code: "unavailable"`.

### `GET /v1/anime/{malId}`

Looks up a single anime by MyAnimeList id. Tries AniList first, falls back to Jikan on error/timeout; result is cached.

**Request**

Path param: `malId` (positive integer). No query params, no body.

**Response — success**

- `200 OK` — body is `AnimeSummary`.

**Response — error**

- `400 Bad Request` — `malId` isn't a positive integer. Body: `ErrorResponse` with `code: "invalid_request"`.
- `404 Not Found` — neither AniList nor Jikan has a match for `malId`. Body: `ErrorResponse` with `code: "not_found"`.
- `500 Internal Server Error` — both upstream sources failed unexpectedly. Body: `ErrorResponse` with `code: "internal_error"`.

**Example**

```json
// GET /v1/anime/16498

// Response 200
{ "malId": 16498, "titleEnglish": "Attack on Titan", "titleJp": "進撃の巨人", "image": "https://...", "score": 8.5, "episodes": 25, "year": 2013, "season": "spring", "status": "Finished Airing", "format": "TV", "genres": ["Action", "Drama"], "studios": ["Wit Studio"] }
```

### `GET /v1/anime/search`

Searches AniList (falling back to Jikan on error/timeout) by title.

**Request**

Query params:
- `q` (string, required) — search term.
- `limit` (number, optional, default 20, max 50).

**Response — success**

- `200 OK` — body is `AnimeSearchResponse`, even if `data` is an empty array (no matches).

**Response — error**

- `400 Bad Request` — `q` missing/empty, or `limit` out of range. Body: `ErrorResponse` with `code: "invalid_request"`.
- `500 Internal Server Error` — both upstream sources failed unexpectedly. Body: `ErrorResponse` with `code: "internal_error"`.

**Example**

```json
// GET /v1/anime/search?q=blue+lock&limit=10

// Response 200
{ "data": [{ "malId": 20958, "titleEnglish": "Blue Lock", "titleJp": null, "image": "https://...", "score": 8.3, "episodes": 24, "year": 2022, "season": "fall", "status": "Finished Airing", "format": "TV", "genres": ["Sports"], "studios": ["8bit"] }] }
```

### `GET /v1/anime/{malId}/characters`

Lists cast for a given anime. Tries AniList first, falls back to Jikan on error/timeout; result is cached.

**Request**

Path param: `malId` (positive integer). No query params, no body.

**Response — success**

- `200 OK` — body is `{ data: CharacterSummary[] }`, even if `data` is an empty array.

**Response — error**

- `400 Bad Request` — `malId` isn't a positive integer. Body: `ErrorResponse` with `code: "invalid_request"`.
- `404 Not Found` — neither AniList nor Jikan has a match for `malId`. Body: `ErrorResponse` with `code: "not_found"`.
- `500 Internal Server Error` — both upstream sources failed unexpectedly. Body: `ErrorResponse` with `code: "internal_error"`.

**Example**

```json
// GET /v1/anime/16498/characters

// Response 200
{ "data": [{ "malId": 40882, "name": "Eren Yeager", "image": "https://...", "role": "Main" }] }
```

## Auth

None in v1. All endpoints are public/unauthenticated for the MVP. If `kyomei_api` takes on persistent per-user state (watchlist sync, saved preferences), token-based auth will be added here as a breaking contract change — do not assume it exists until this section is updated.

## Proposed / Not Yet Confirmed

These are plausible next endpoints based on the direction of the project, but **they are not part of the current contract**. Do not implement against these until they're moved into the "Endpoints" section above by mutual agreement.

### `POST /v1/recommendations`

Matches the original v1 draft of this contract; not implemented until personalization/auth work begins, per the setup checklist's phasing. Kept here so the shape is agreed on ahead of that phase.

Takes the user's watch history and returns a ranked list of recommended anime the user hasn't already logged.

**Request**

No path or query params. Body:

```typescript
interface RecommendationsRequest {
  history: HistoryEntry[]; // required, can be empty array for "cold start" recs
  limit?: number;          // optional, default 20, max 50
}
```

**Response — success**

```typescript
interface RecommendedAnime extends AnimeSummary {
  matchScore: number; // 0.0–1.0, confidence/relevance of this recommendation
}

interface RecommendationsResponse {
  data: RecommendedAnime[];
}
```

- `200 OK` — `RecommendationsResponse`, even if `data` is an empty array (e.g. nothing left to recommend).

**Response — error**

- `400 Bad Request` — malformed body, `limit` out of range, or a `HistoryEntry.malId` that isn't a positive integer. Body: `ErrorResponse` with `code: "invalid_request"`.
- `500 Internal Server Error` — unexpected failure (e.g. upstream data source failure inside kyomei_api). Body: `ErrorResponse` with `code: "internal_error"`.

**Example**

```json
// Request
{ "history": [{ "malId": 16498, "status": "completed", "score": 9 }], "limit": 10 }

// Response 200
{ "data": [{ "malId": 20958, "titleEnglish": "Blue Lock", "titleJp": null, "image": "https://...", "score": 8.3, "episodes": 24, "year": 2022, "season": "fall", "status": "Finished Airing", "format": "TV", "genres": ["Sports"], "studios": ["8bit"], "matchScore": 0.87 }] }
```

### Other proposed endpoints

- `GET /v1/watchlist` / `PUT /v1/watchlist` — server-side sync of `WatchlistEntry[]`, if watchlist state moves off the client.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-13 | Reset v1 scope to match `docs/fastapi-backend-setup-checklist.md`: `GET /v1/anime/{malId}`, `GET /v1/anime/search`, `GET /v1/anime/{malId}/characters` are now in-scope (AniList-primary/Jikan-fallback orchestration + caching), with new shared types `AnimeSearchResponse`/`CharacterSummary`. `POST /v1/recommendations` moved to Proposed until personalization/auth work begins. |
| 2026-08-10 | Initial contract: `GET /health`, `POST /v1/recommendations`, shared `AnimeSummary`/`HistoryEntry`/`ErrorResponse` types. |
