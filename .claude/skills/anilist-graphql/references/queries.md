# AniList worked query examples

Run any of these with `scripts/query.py`:

```
python scripts/query.py '<query string>' '<json variables>'
```

## 1. Search media by title

```graphql
query ($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      idMal
      title { romaji english }
      coverImage { large }
      averageScore
      episodes
      seasonYear
      season
      status
      format
      genres
      studios(isMain: true) { nodes { name } }
    }
  }
}
```
```json
{ "search": "attack on titan", "page": 1, "perPage": 10 }
```
Returns a ranked list of matching anime. Swap `type: ANIME` for `type: MANGA` to search manga instead.

## 2. Get media details by ID

```graphql
query ($idMal: Int) {
  Media(idMal: $idMal, type: ANIME) {
    id
    idMal
    title { romaji english native }
    description
    coverImage { large }
    bannerImage
    averageScore
    episodes
    status
    genres
  }
}
```
```json
{ "idMal": 16498 }
```
Returns a single anime by its MyAnimeList ID. If you only have AniList's own ID (e.g. for something with no MAL mapping, like most characters), query by `id: $id` instead of `idMal: $idMal`.

## 3. Get characters for a media

```graphql
query ($id: Int) {
  Media(id: $id) {
    title { romaji }
    characters(sort: [ROLE, RELEVANCE], perPage: 25) {
      edges {
        role
        node {
          id
          name { full }
          image { large }
        }
      }
    }
  }
}
```
```json
{ "id": 16498 }
```
Returns the cast sorted by role (`MAIN` before `SUPPORTING`) then relevance. Use `id` (AniList's ID), not `idMal`, since you'd typically get here by first resolving the media via query #2.

## 4. Fetch a user's list by username

```graphql
query ($userName: String, $type: MediaType) {
  MediaListCollection(userName: $userName, type: $type) {
    lists {
      name
      entries {
        status
        score
        progress
        media {
          idMal
          title { romaji }
          coverImage { large }
        }
      }
    }
  }
}
```
```json
{ "userName": "Josh", "type": "ANIME" }
```
Returns the user's full anime list, grouped into named lists (e.g. "Watching", "Completed", "Planning"). Only public lists are visible without a Bearer token.

## 5. Get a user's profile by username

```graphql
query ($userName: String) {
  User(name: $userName) {
    id
    name
    avatar { large }
    about
    statistics {
      anime { count meanScore episodesWatched }
      manga { count meanScore chaptersRead }
    }
  }
}
```
```json
{ "userName": "Josh" }
```
Returns profile info and aggregate stats. For the currently-authenticated user (needs a Bearer token), use `Viewer { ... }` with no arguments instead.

## 6. Paginate results

```graphql
query ($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      total
      currentPage
      lastPage
      hasNextPage
    }
    media(search: $search, type: ANIME) {
      idMal
      title { romaji }
    }
  }
}
```
```json
{ "search": "gundam", "page": 1, "perPage": 50 }
```
`perPage` caps at 50. Loop by incrementing `page` and stopping once `pageInfo.hasNextPage` is `false` — don't rely on `total` alone since it can change between requests for actively-updated data.
