"""Domain logic: Provider interface (get_by_id, search, get_characters) and
AniList->Jikan fallback orchestration.

This package defines HTTP-agnostic domain types and the Provider interface
that app/anilist/ and app/jikan/ clients implement, and that the future
app/anime/service.py fallback orchestrator consumes.
"""

from app.anime.errors import AnimeError, AnimeNotFoundError, UpstreamError
from app.anime.models import AnimeSummary, CharacterSummary
from app.anime.provider import Provider

__all__ = [
    "AnimeError",
    "AnimeNotFoundError",
    "AnimeSummary",
    "CharacterSummary",
    "Provider",
    "UpstreamError",
]
