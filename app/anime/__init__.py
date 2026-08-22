"""Domain logic: Provider interface (get_by_id, search, get_characters) and
AniList-backed orchestration.

This package defines HTTP-agnostic domain types and the Provider interface
that app/anilist/ implements, and that the future app/anime/service.py
orchestrator consumes.
"""

from app.anime.errors import AnimeError, AnimeNotFoundError, UpstreamError
from app.anime.models import AnimeDetail, AnimeSummary, CharacterSummary, VoiceActorSummary
from app.anime.provider import Provider

__all__ = [
    "AnimeDetail",
    "AnimeError",
    "AnimeNotFoundError",
    "AnimeSummary",
    "CharacterSummary",
    "Provider",
    "UpstreamError",
    "VoiceActorSummary",
]
