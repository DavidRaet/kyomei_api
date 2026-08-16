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


class CharacterSummaryOut(CamelModel):
    mal_id: int
    name: str
    image: str
    role: str


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
