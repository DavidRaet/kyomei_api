from fastapi import APIRouter, Depends, Path, Query, Request

from app.anime.provider import Provider
from app.routers.schemas import AnimeSearchOut, AnimeSummaryOut, CharactersOut, CharacterSummaryOut

router = APIRouter(prefix="/v1/anime", tags=["anime"])


def get_provider(request: Request) -> Provider:
    return request.app.state.provider


@router.get("/search", response_model=AnimeSearchOut)
async def search_anime(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    provider: Provider = Depends(get_provider),
) -> AnimeSearchOut:
    results = await provider.search(q, limit)
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
