from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from app.anime.provider import Provider
from app.routers.schemas import AnimeSearchOut, AnimeSummaryOut, CharactersOut, CharacterSummaryOut

router = APIRouter(prefix="/v1/anime", tags=["anime"])

_SEASON_BY_MONTH: dict[int, Literal["winter", "spring", "summer", "fall"]] = {
    1: "winter",
    2: "winter",
    3: "winter",
    4: "spring",
    5: "spring",
    6: "spring",
    7: "summer",
    8: "summer",
    9: "summer",
    10: "fall",
    11: "fall",
    12: "fall",
}


def get_provider(request: Request) -> Provider:
    return request.app.state.provider


def _current_season_year() -> tuple[Literal["winter", "spring", "summer", "fall"], int]:
    now = datetime.now(UTC)
    return _SEASON_BY_MONTH[now.month], now.year


@router.get("/search", response_model=AnimeSearchOut)
async def search_anime(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    provider: Provider = Depends(get_provider),
) -> AnimeSearchOut:
    results = await provider.search(q, limit)
    return AnimeSearchOut(data=[AnimeSummaryOut.model_validate(r, from_attributes=True) for r in results])


@router.get("/trending", response_model=AnimeSearchOut)
async def get_trending_anime(
    limit: int = Query(default=20, ge=1, le=50),
    provider: Provider = Depends(get_provider),
) -> AnimeSearchOut:
    results = await provider.get_trending(limit)
    return AnimeSearchOut(data=[AnimeSummaryOut.model_validate(r, from_attributes=True) for r in results])


@router.get("/seasonal", response_model=AnimeSearchOut)
async def get_seasonal_anime(
    season: Literal["winter", "spring", "summer", "fall"] | None = Query(default=None),
    year: int | None = Query(default=None, ge=1940),
    limit: int = Query(default=20, ge=1, le=50),
    provider: Provider = Depends(get_provider),
) -> AnimeSearchOut:
    default_season, default_year = _current_season_year()
    results = await provider.get_seasonal(year or default_year, season or default_season, limit)
    return AnimeSearchOut(data=[AnimeSummaryOut.model_validate(r, from_attributes=True) for r in results])


@router.get("/{mal_id}", response_model=AnimeSummaryOut)
async def get_anime(
    mal_id: int = Path(..., gt=0),
    provider: Provider = Depends(get_provider),
) -> AnimeSummaryOut:
    summary = await provider.get_by_id(mal_id)
    return AnimeSummaryOut.model_validate(summary, from_attributes=True)


@router.get("/{mal_id}/characters", response_model=CharactersOut)
async def get_anime_characters(
    mal_id: int = Path(..., gt=0),
    provider: Provider = Depends(get_provider),
) -> CharactersOut:
    characters = await provider.get_characters(mal_id)
    return CharactersOut(data=[CharacterSummaryOut.model_validate(c, from_attributes=True) for c in characters])
