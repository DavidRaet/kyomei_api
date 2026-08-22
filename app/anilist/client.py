"""Async AniList GraphQL client — primary anime data source.

Implements the app.anime.provider.Provider protocol structurally (no
subclassing required).
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from app.anime.errors import AnimeNotFoundError, UpstreamError, UpstreamUnavailableError
from app.anime.models import AnimeDetail, AnimeSummary, CharacterSummary, VoiceActorSummary
from app.logging_config import logger

_DEFAULT_ENDPOINT = "https://graphql.anilist.co"
_CHARACTERS_PAGE_SIZE = 25

_MEDIA_FIELDS = """
    idMal
    title {
      english
      romaji
      native
    }
    coverImage {
      large
    }
    averageScore
    episodes
    seasonYear
    season
    status
    format
    genres
    studios(isMain: true) {
      nodes {
        name
      }
    }
"""

_MEDIA_DETAIL_FIELDS = f"""
    {_MEDIA_FIELDS}
    description
    duration
    startDate {{
      year
      month
      day
    }}
    endDate {{
      year
      month
      day
    }}
    trailer {{
      thumbnail
    }}
"""

_GET_ANIME_BY_ID_QUERY = f"""
query GetAnimeById($idMal: Int) {{
  Media(idMal: $idMal, type: ANIME) {{
    {_MEDIA_DETAIL_FIELDS}
  }}
}}
"""

_SEARCH_ANIME_QUERY = f"""
query SearchAnime($search: String, $perPage: Int) {{
  Page(page: 1, perPage: $perPage) {{
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {{
      {_MEDIA_FIELDS}
    }}
  }}
}}
"""

_TRENDING_ANIME_QUERY = f"""
query TrendingAnime($perPage: Int) {{
  Page(page: 1, perPage: $perPage) {{
    media(type: ANIME, sort: TRENDING_DESC) {{
      {_MEDIA_FIELDS}
    }}
  }}
}}
"""

_SEASONAL_ANIME_QUERY = f"""
query SeasonalAnime($season: MediaSeason, $seasonYear: Int, $perPage: Int) {{
  Page(page: 1, perPage: $perPage) {{
    media(type: ANIME, season: $season, seasonYear: $seasonYear, sort: POPULARITY_DESC) {{
      {_MEDIA_FIELDS}
    }}
  }}
}}
"""

_GET_ANIME_CHARACTERS_QUERY = """
query GetAnimeCharacters($idMal: Int, $perPage: Int) {
  Media(idMal: $idMal, type: ANIME) {
    idMal
    characters(sort: [ROLE, RELEVANCE], perPage: $perPage) {
      edges {
        role
        voiceActors {
          languageV2
          name {
            full
          }
          image {
            large
          }
        }
        node {
          id
          name {
            full
          }
          image {
            large
          }
          favourites
        }
      }
    }
  }
}
"""

_STATUS_MAP = {
    "FINISHED": "Finished Airing",
    "RELEASING": "Currently Airing",
    "NOT_YET_RELEASED": "Not yet aired",
    "CANCELLED": "Cancelled",
    "HIATUS": "On Hiatus",
}

_FORMAT_MAP = {
    "TV": "TV",
    "TV_SHORT": "TV Short",
    "MOVIE": "Movie",
    "SPECIAL": "Special",
    "OVA": "OVA",
    "ONA": "ONA",
    "MUSIC": "Music",
}


def _summary_kwargs(media: dict[str, Any]) -> dict[str, Any]:
    title = media.get("title") or {}
    title_english = title.get("english") or title.get("romaji") or title.get("native") or "Unknown Title"

    average_score = media.get("averageScore")
    score = round(average_score / 10, 1) if average_score is not None else None

    season = media.get("season")

    raw_status = media.get("status")
    status = _STATUS_MAP.get(raw_status, (raw_status or "Unknown").replace("_", " ").title())

    raw_format = media.get("format")
    format_ = _FORMAT_MAP.get(raw_format, (raw_format or "Unknown").replace("_", " ").title())

    studios = [node["name"] for node in (media.get("studios") or {}).get("nodes") or []]

    return {
        "mal_id": media["idMal"],
        "title_english": title_english,
        "title_jp": title.get("native"),
        "image": (media.get("coverImage") or {}).get("large") or "",
        "score": score,
        "episodes": media.get("episodes"),
        "year": media.get("seasonYear"),
        "season": season.lower() if season else None,
        "status": status,
        "format": format_,
        "genres": media.get("genres") or [],
        "studios": studios,
    }


def _media_to_summary(media: dict[str, Any]) -> AnimeSummary:
    try:
        return AnimeSummary(**_summary_kwargs(media))
    except (ValidationError, KeyError, TypeError) as exc:
        raise UpstreamError("AniList returned malformed anime data") from exc


def _fuzzy_date_to_iso(date: dict[str, Any] | None) -> str | None:
    if not date:
        return None
    year, month, day = date.get("year"), date.get("month"), date.get("day")
    if year is None or month is None or day is None:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _media_to_detail(media: dict[str, Any]) -> AnimeDetail:
    title = media.get("title") or {}
    try:
        return AnimeDetail(
            **_summary_kwargs(media),
            title_romaji=title.get("romaji"),
            synopsis=media.get("description"),
            duration_minutes=media.get("duration"),
            aired_from=_fuzzy_date_to_iso(media.get("startDate")),
            aired_to=_fuzzy_date_to_iso(media.get("endDate")),
            trailer_image=(media.get("trailer") or {}).get("thumbnail"),
        )
    except (ValidationError, KeyError, TypeError, ValueError) as exc:
        raise UpstreamError("AniList returned malformed anime data") from exc


def _staff_to_voice_actor(staff: dict[str, Any]) -> VoiceActorSummary | None:
    name = (staff.get("name") or {}).get("full")
    if not name:
        return None
    try:
        return VoiceActorSummary(
            language=staff.get("languageV2") or "Unknown",
            name=name,
            image=(staff.get("image") or {}).get("large") or "",
        )
    except (ValidationError, KeyError, TypeError, AttributeError) as exc:
        raise UpstreamError("AniList returned malformed character data") from exc


def _edge_to_character(edge: dict[str, Any]) -> CharacterSummary | None:
    # AniList's Character type has no MAL id mapping — its own internal `id`
    # is the only stable identifier available, so it fills the mal_id field.
    node = edge.get("node") or {}
    if node.get("id") is None:
        return None

    voice_actors = [
        va for va in (_staff_to_voice_actor(staff) for staff in edge.get("voiceActors") or []) if va is not None
    ]

    try:
        return CharacterSummary(
            mal_id=node["id"],
            name=(node.get("name") or {}).get("full") or "Unknown",
            image=(node.get("image") or {}).get("large") or "",
            role=(edge.get("role") or "Unknown").capitalize(),
            favorites=node.get("favourites") or 0,
            voice_actors=voice_actors,
        )
    except (ValidationError, KeyError, TypeError, AttributeError) as exc:
        raise UpstreamError("AniList returned malformed character data") from exc


class AniListClient:
    """Async GraphQL client for AniList, the primary anime data source."""

    def __init__(
        self,
        endpoint: str = _DEFAULT_ENDPOINT,
        *,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._endpoint = endpoint
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(timeout=timeout)
            self._owns_client = True

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AniListClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def _execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(self._endpoint, json={"query": query, "variables": variables})
        except httpx.TimeoutException as exc:
            raise UpstreamError(f"AniList request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"AniList request failed: {exc}") from exc

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise UpstreamError(f"AniList returned malformed JSON (HTTP {response.status_code})") from exc

        if response.status_code >= 400 and response.status_code != 404:
            logger.warning("AniList returned HTTP %s: %s", response.status_code, payload.get("errors"))
            raise UpstreamUnavailableError(f"AniList returned an error response (HTTP {response.status_code}).")

        if response.status_code != 404 and "data" not in payload:
            logger.warning("AniList response missing data: %s", payload.get("errors"))
            raise UpstreamUnavailableError("AniList responded without the expected data.")

        return payload

    async def get_by_id(self, mal_id: int) -> AnimeDetail:
        payload = await self._execute(_GET_ANIME_BY_ID_QUERY, {"idMal": mal_id})
        media = (payload.get("data") or {}).get("Media")
        if media is None:
            raise AnimeNotFoundError(mal_id)
        return _media_to_detail(media)

    async def search(self, q: str, limit: int = 20) -> list[AnimeSummary]:
        payload = await self._execute(_SEARCH_ANIME_QUERY, {"search": q, "perPage": limit})
        if payload.get("errors"):
            raise UpstreamError(f"AniList search failed: {payload['errors']}")

        media_list = ((payload.get("data") or {}).get("Page") or {}).get("media") or []
        return [_media_to_summary(media) for media in media_list if media.get("idMal") is not None]

    async def get_trending(self, limit: int = 20) -> list[AnimeSummary]:
        payload = await self._execute(_TRENDING_ANIME_QUERY, {"perPage": limit})
        if payload.get("errors"):
            raise UpstreamError(f"AniList trending query failed: {payload['errors']}")

        media_list = ((payload.get("data") or {}).get("Page") or {}).get("media") or []
        return [_media_to_summary(media) for media in media_list if media.get("idMal") is not None]

    async def get_seasonal(self, year: int, season: str, limit: int = 20) -> list[AnimeSummary]:
        variables = {"season": season.upper(), "seasonYear": year, "perPage": limit}
        payload = await self._execute(_SEASONAL_ANIME_QUERY, variables)
        if payload.get("errors"):
            raise UpstreamError(f"AniList seasonal query failed: {payload['errors']}")

        media_list = ((payload.get("data") or {}).get("Page") or {}).get("media") or []
        return [_media_to_summary(media) for media in media_list if media.get("idMal") is not None]

    async def get_characters(self, mal_id: int) -> list[CharacterSummary]:
        payload = await self._execute(_GET_ANIME_CHARACTERS_QUERY, {"idMal": mal_id, "perPage": _CHARACTERS_PAGE_SIZE})
        media = (payload.get("data") or {}).get("Media")
        if media is None:
            raise AnimeNotFoundError(mal_id)

        edges = (media.get("characters") or {}).get("edges") or []
        characters = (_edge_to_character(edge) for edge in edges)
        return [character for character in characters if character is not None]
