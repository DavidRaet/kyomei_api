class AnimeError(Exception):
    """Base class for domain-level anime errors."""


class AnimeNotFoundError(AnimeError):
    """Raised when neither AniList nor Jikan has the requested anime."""

    def __init__(self, mal_id: int):
        self.mal_id = mal_id
        super().__init__(f"Anime {mal_id} not found")


class UpstreamError(AnimeError):
    """Raised when an upstream provider (AniList/Jikan) fails or times out and no fallback succeeds."""
