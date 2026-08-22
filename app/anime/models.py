from pydantic import BaseModel


class AnimeSummary(BaseModel):
    mal_id: int
    title_english: str
    title_jp: str | None = None
    image: str
    score: float | None = None
    episodes: int | None = None
    year: int | None = None
    season: str | None = None
    status: str
    format: str
    genres: list[str] = []
    studios: list[str] = []


class AnimeDetail(AnimeSummary):
    title_romaji: str | None = None
    synopsis: str | None = None
    duration_minutes: int | None = None
    aired_from: str | None = None
    aired_to: str | None = None
    trailer_image: str | None = None


class VoiceActorSummary(BaseModel):
    language: str
    name: str
    image: str


class CharacterSummary(BaseModel):
    mal_id: int
    name: str
    image: str
    role: str
    favorites: int
    voice_actors: list[VoiceActorSummary]
