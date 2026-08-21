# Kyomei API Contract

**Last updated:** 2026-08-10

This document is the single source of truth for the HTTP API boundary between:

- **`kyomei_api`** — Go backend service, owns recommendation logic and (eventually) any server-side user state.
- **`kyomei_0`** — TypeScript/Vite frontend, currently calls AniList/Jikan directly for anime metadata/browsing and will call `kyomei_api` for personalized recommendations.

This file is copy-pasted verbatim into both repositories. Neither side needs to read the other's source code — only this contract. If an endpoint, field, or status code isn't listed here, it doesn't exist yet. Propose changes via a PR to this file in both repos before implementing.

## Scope

**In scope for `kyomei_api` (v1):**
- Turning a user's watch history into a ranked anime recommendation list.
- Basic service health reporting.

**Explicitly out of scope for `kyomei_api` (v1):**
- Trending/seasonal/search anime browsing — this stays client-side in `kyomei_0` (`src/api/anilist.ts`, `src/api/jikan.ts`) against AniList/Jikan directly. `kyomei_api` does not proxy or duplicate this.
- Any persistent server-side storage of watchlists or user accounts. `kyomei_0` currently owns watchlist state locally (see `WatchlistEntry`). If/when this moves server-side, it will be added to this contract as a new versioned endpoint — see "Proposed / Not Yet Confirmed" below.

## Conventions

- Base path: all endpoints are prefixed with `/v1` except the health check.
- All request/response bodies are `application/json`.
- Field names in JSON bodies are `camelCase`. Go struct fields use `json:"camelCase"` tags to match; TS interfaces need no transformation.
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

// Matches the frontend's WatchlistStatus (src/types/watchlist.ts).
type WatchlistStatus = 'watching' | 'completed' | 'planning';

// A single history entry the client sends to describe what the user has watched.
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

### `POST /v1/recommendations`

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

## Auth

None in v1. All endpoints are public/unauthenticated for the MVP. If `kyomei_api` takes on persistent per-user state (watchlist sync, saved preferences), token-based auth will be added here as a breaking contract change — do not assume it exists until this section is updated.

## Proposed / Not Yet Confirmed

These are plausible next endpoints based on the direction of the project, but **they are not part of the current contract**. Do not implement against these until they're moved into the "Endpoints" section above by mutual agreement.

- `GET /v1/watchlist` / `PUT /v1/watchlist` — server-side sync of `WatchlistEntry[]`, if watchlist state moves off the client.
- `GET /v1/anime/:malId` — server-side anime detail lookup, only needed if `kyomei_api` starts caching/aggregating AniList+Jikan data instead of the client doing it directly.

## Change Log

| Date | Change |
|------|--------|
| 2026-08-10 | Initial contract: `GET /health`, `POST /v1/recommendations`, shared `AnimeSummary`/`HistoryEntry`/`ErrorResponse` types. |
