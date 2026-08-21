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


class CharacterSummary(BaseModel):
    mal_id: int
    name: str
    image: str
    role: str
