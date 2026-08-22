from typing import Protocol, runtime_checkable

from app.anime.models import AnimeDetail, AnimeSummary, CharacterSummary


@runtime_checkable
class Provider(Protocol):
    """Upstream-agnostic anime data source, mirroring the frontend's animeProvider.ts abstraction.
    AniList is currently the only implementation."""

    async def get_by_id(self, mal_id: int) -> AnimeDetail:
        """Raises AnimeNotFoundError if this provider doesn't have the anime."""
        ...

    async def search(self, q: str, limit: int = 20) -> list[AnimeSummary]:
        """Empty results are valid; never raises AnimeNotFoundError."""
        ...

    async def get_characters(self, mal_id: int) -> list[CharacterSummary]:
        """Raises AnimeNotFoundError if the anime itself doesn't exist."""
        ...

    async def get_trending(self, limit: int = 20) -> list[AnimeSummary]:
        """Empty results are valid; never raises AnimeNotFoundError."""
        ...

    async def get_seasonal(self, year: int, season: str, limit: int = 20) -> list[AnimeSummary]:
        """`season` is one of winter/spring/summer/fall (lowercase).
        Empty results are valid; never raises AnimeNotFoundError."""
        ...
