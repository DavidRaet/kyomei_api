from typing import Protocol, runtime_checkable

from app.anime.models import AnimeSummary, CharacterSummary


@runtime_checkable
class Provider(Protocol):
    """Upstream-agnostic anime data source, mirroring the frontend's animeProvider.ts abstraction.
    AniList is currently the only implementation."""

    async def get_by_id(self, mal_id: int) -> AnimeSummary:
        """Raises AnimeNotFoundError if this provider doesn't have the anime."""
        ...

    async def search(self, q: str, limit: int = 20) -> list[AnimeSummary]:
        """Empty results are valid; never raises AnimeNotFoundError."""
        ...

    async def get_characters(self, mal_id: int) -> list[CharacterSummary]:
        """Raises AnimeNotFoundError if the anime itself doesn't exist."""
        ...
