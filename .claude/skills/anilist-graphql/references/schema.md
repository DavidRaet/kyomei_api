# AniList schema — practical fields

Not the full schema (see https://anilist.github.io/ApiV2-GraphQL-Docs/ for that) — just the fields you'll actually reach for on each type.

## Media (anime/manga)

| Field | Notes |
|---|---|
| `id` | AniList's internal ID. Always present. |
| `idMal` | MyAnimeList ID. Can be `null` for entries with no MAL mapping. |
| `title { romaji english native }` | Pick whichever's non-null; `english` is often `null` for niche titles. |
| `type` | Enum: `ANIME` \| `MANGA`. |
| `format` | Enum: `TV`, `TV_SHORT`, `MOVIE`, `SPECIAL`, `OVA`, `ONA`, `MUSIC`, `MANGA`, `NOVEL`, `ONE_SHOT`. |
| `status` | Enum: `FINISHED`, `RELEASING`, `NOT_YET_RELEASED`, `CANCELLED`, `HIATUS`. |
| `description` | HTML-ish markup (`<br>`, `<i>`) embedded in the string — strip/render as needed. |
| `startDate { year month day }` / `endDate { ... }` | Any field can be `null` (e.g. ongoing series have `null` `endDate`). |
| `season` / `seasonYear` | `season` enum: `WINTER`, `SPRING`, `SUMMER`, `FALL`. |
| `episodes` / `duration` (anime) | `duration` is minutes per episode. |
| `chapters` / `volumes` (manga) | |
| `genres` | `[String]`, e.g. `["Action", "Comedy"]`. |
| `averageScore` | **0–100**, not 0–10. Divide by 10 for a 0–10 scale (see `app/anilist/client.py` in kyomei_api). |
| `popularity` | Raw favorite/list-add count, int. |
| `coverImage { large medium color }` | `color` is a hex string used as a placeholder/dominant color. |
| `bannerImage` | Wide banner image URL, can be `null`. |
| `studios(isMain: true) { nodes { name } }` | Filter to main studio(s); omit the arg to get all studios including producers. |
| `characters(sort: [ROLE, RELEVANCE]) { edges { role node { ... } } }` | See Character below. |
| `staff { edges { role node { ... } } }` | See Staff below. |
| `relations { edges { relationType node { ... } } }` | Sequels/prequels/adaptations, etc. |

Enums are unquoted identifiers in GraphQL: `type: ANIME`, not `type: "ANIME"`.

## Character

| Field | Notes |
|---|---|
| `id` | No MAL mapping exists for characters — don't expect an `idMal`. |
| `name { full native alternative }` | `alternative` is `[String]` of aliases/nicknames. |
| `image { large medium }` | |
| `description` | Markdown-ish, often long. |
| `gender`, `dateOfBirth { year month day }`, `age` | Frequently `null` — don't assume presence. |
| `media(perPage: N) { edges { node { title { romaji } } } }` | Appearances, for reverse lookup from character → shows. |

Fetched via `Media.characters` (see queries.md #3) or standalone via `Character(id: $id) { ... }`.

## Staff

| Field | Notes |
|---|---|
| `id` | |
| `name { full native }` | |
| `image { large }` | |
| `description` | |
| `primaryOccupations` | `[String]`, e.g. `["Director", "Screenplay"]`. |
| `staffMedia(perPage: N) { edges { staffRole node { title { romaji } } } }` | Works they contributed to. |
| `characters(perPage: N) { nodes { name { full } } }` | For voice actors: characters they've voiced. |

## User

| Field | Notes |
|---|---|
| `id`, `name` | `name` is the username, used in lookups (`User(name: $userName)`). |
| `avatar { large medium }`, `bannerImage` | |
| `about` | User's bio, markdown. |
| `statistics { anime { count meanScore episodesWatched genres { genre count } } manga { count meanScore chaptersRead } }` | Aggregate stats; `genres` is a breakdown array. |
| `siteUrl` | Link to their AniList profile page. |

The currently-authenticated user (requires a Bearer token) is fetched via `Viewer { ... }` instead of `User(name: ...)`.

## MediaList (a user's list entries)

Not fetched standalone — always through `MediaListCollection` (bulk, by username) or `MediaList` (single entry, needs auth for private lists).

| Field | Notes |
|---|---|
| `MediaListCollection(userName: $userName, type: $type) { lists { name entries { ... } } }` | `type`: `ANIME` \| `MANGA`. Groups entries by list name (e.g. "Watching", "Completed") unless `forceSingleCompletedList` is used. |
| `entries[].status` | Enum: `CURRENT`, `PLANNING`, `COMPLETED`, `DROPPED`, `PAUSED`, `REPEATING`. |
| `entries[].score` | User's personal score; scale depends on the user's scoring format setting (default 0–10 with decimals allowed). |
| `entries[].progress` | Episodes/chapters consumed so far. |
| `entries[].media { ...Media fields }` | Embed any Media fields you need here. |

## Common gotchas

- `averageScore` and `meanScore` are 0–100 scale; user `score` on a list entry is whatever scale that user configured (check `User.mediaListOptions.scoreFormat`).
- Almost everything nullable can genuinely be `null` — AniList's data is community-sourced and incomplete for niche titles/characters.
- `search` filters (title search) only work inside `Page.media(search: $search)` / `Page.characters(search: $search)`, not on the singular `Media`/`Character` root fields.
