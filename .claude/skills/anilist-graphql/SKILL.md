---
name: anilist-graphql
description: Use when querying the AniList GraphQL API for anime/manga metadata, character/staff details, or user profiles and lists — building or debugging GraphQL queries against graphql.anilist.co, looking up Media/Character/Staff/User/MediaList fields, or handling AniList rate-limit (429) responses.
---

# AniList GraphQL

## Overview

AniList exposes a single GraphQL endpoint for anime/manga data, cast/staff info, and user profiles/lists. No REST API, no per-resource URLs — every request is a POST with a `query` and optional `variables`.

## Endpoint

```
POST https://graphql.anilist.co
Content-Type: application/json

{ "query": "...", "variables": { ... } }
```

## Auth

- **Public reads need no auth**: Media/Character/Staff search and lookup, and public User profiles/lists.
- **OAuth2 Bearer token required for**: mutations (list updates, favorites, following) and viewer-scoped queries (the `Viewer` field, private lists). Get a token via AniList's OAuth2 flow (Implicit or Authorization Code grant, configured in an AniList API client at anilist.co/settings/developer).
- `scripts/query.py` in this skill is read-only/public-only — it does not handle tokens.

## Rate limits

AniList rate-limits per IP and returns `429` with a `Retry-After` header (seconds to wait) when exceeded. Successful responses carry `X-RateLimit-Limit` / `X-RateLimit-Remaining` headers. The limit is dynamic — AniList has run degraded (~30 req/min) periods well below its historical 90 req/min — so never hardcode a request rate; always honor `Retry-After` and back off on 429.

## References

- `references/schema.md` — practical fields for Media, Character, Staff, User, MediaList (not the full schema).
- `references/queries.md` — worked query examples: search, lookup by ID, characters, user lists, user profile, pagination.
- `scripts/query.py` — POST a query+variables to the endpoint with built-in 429 backoff; returns clean JSON.
