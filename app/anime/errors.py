class AnimeError(Exception):
    """Base class for domain-level anime errors."""


class AnimeNotFoundError(AnimeError):
    """Raised when AniList doesn't have the requested anime."""

    def __init__(self, mal_id: int):
        self.mal_id = mal_id
        super().__init__(f"Anime {mal_id} not found")


class UpstreamError(AnimeError):
    """Raised when the upstream AniList provider fails or times out."""
