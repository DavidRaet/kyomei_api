from pydantic import BaseModel, ConfigDict, alias_generators


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=alias_generators.to_camel, populate_by_name=True)


class AnimeSummaryOut(CamelModel):
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


class AnimeDetailOut(AnimeSummaryOut):
    title_romaji: str | None = None
    synopsis: str | None = None
    duration_minutes: int | None = None
    aired_from: str | None = None
    aired_to: str | None = None
    trailer_image: str | None = None


class VoiceActorSummaryOut(CamelModel):
    language: str
    name: str
    image: str


class CharacterSummaryOut(CamelModel):
    mal_id: int
    name: str
    image: str
    role: str
    favorites: int
    voice_actors: list[VoiceActorSummaryOut]


class AnimeSearchOut(CamelModel):
    data: list[AnimeSummaryOut]
    total: int | None = None


class CharactersOut(CamelModel):
    data: list[CharacterSummaryOut]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
