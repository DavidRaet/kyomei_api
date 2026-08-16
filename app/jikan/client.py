"""Async Jikan REST client — fallback anime data source.

Implements the app.anime.provider.Provider protocol structurally (no
subclassing required).
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from app.anime.errors import AnimeNotFoundError, UpstreamError
from app.anime.models import AnimeSummary, CharacterSummary

_DEFAULT_BASE_URL = "https://api.jikan.moe/v4"


def _anime_to_summary(anime: dict[str, Any]) -> AnimeSummary:
    title_english = anime.get("title_english") or anime.get("title") or "Unknown Title"

    raw_score = anime.get("score")
    score = raw_score if raw_score else None

    images = anime.get("images") or {}
    jpg = images.get("jpg") or {}
    webp = images.get("webp") or {}
    image = (
        jpg.get("large_image_url") or jpg.get("image_url") or webp.get("large_image_url") or webp.get("image_url") or ""
    )

    genres = [genre["name"] for genre in anime.get("genres") or []]
    studios = [studio["name"] for studio in anime.get("studios") or []]

    try:
        return AnimeSummary(
            mal_id=anime["mal_id"],
            title_english=title_english,
            title_jp=anime.get("title_japanese"),
            image=image,
            score=score,
            episodes=anime.get("episodes"),
            year=anime.get("year"),
            season=anime.get("season"),
            status=anime.get("status") or "Unknown",
            format=anime.get("type") or "Unknown",
            genres=genres,
            studios=studios,
        )
    except (ValidationError, KeyError, TypeError) as exc:
        raise UpstreamError("Jikan returned malformed anime data") from exc


def _entry_to_character(entry: dict[str, Any]) -> CharacterSummary | None:
    character = entry.get("character") or {}
    if character.get("mal_id") is None:
        return None

    images = character.get("images") or {}
    jpg = images.get("jpg") or {}
    webp = images.get("webp") or {}
    image = jpg.get("image_url") or webp.get("image_url") or ""

    try:
        return CharacterSummary(
            mal_id=character["mal_id"],
            name=character.get("name") or "Unknown",
            image=image,
            role=entry.get("role") or "Unknown",
        )
    except (ValidationError, KeyError, TypeError) as exc:
        raise UpstreamError("Jikan returned malformed character data") from exc


class JikanClient:
    """Async REST client for Jikan, the fallback anime data source."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        *,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(timeout=timeout)
            self._owns_client = True

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> JikanClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = await self._client.get(f"{self._base_url}{path}", params=params)
        except httpx.TimeoutException as exc:
            raise UpstreamError(f"Jikan request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Jikan request failed: {exc}") from exc

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise UpstreamError(f"Jikan returned malformed JSON (HTTP {response.status_code})") from exc

        if response.status_code >= 400 and response.status_code != 404:
            raise UpstreamError(f"Jikan returned HTTP {response.status_code}: {payload.get('message')}")

        if response.status_code == 200 and "data" not in payload:
            raise UpstreamError("Jikan returned HTTP 200 with no data field")

        return payload

    async def get_by_id(self, mal_id: int) -> AnimeSummary:
        payload = await self._get(f"/anime/{mal_id}")
        data = payload.get("data")
        if data is None:
            raise AnimeNotFoundError(mal_id)
        return _anime_to_summary(data)

    async def search(self, q: str, limit: int = 20) -> list[AnimeSummary]:
        payload = await self._get("/anime", params={"q": q, "limit": limit})
        anime_list = payload.get("data") or []
        return [_anime_to_summary(anime) for anime in anime_list if anime.get("mal_id") is not None]

    async def get_characters(self, mal_id: int) -> list[CharacterSummary]:
        payload = await self._get(f"/anime/{mal_id}/characters")
        entries = payload.get("data")
        if entries is None:
            raise AnimeNotFoundError(mal_id)

        characters = (_entry_to_character(entry) for entry in entries)
        return [character for character in characters if character is not None]
