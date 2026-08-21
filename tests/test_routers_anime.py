from fastapi.testclient import TestClient

from app.anime.errors import AnimeNotFoundError, UpstreamError
from app.anime.models import AnimeSummary, CharacterSummary
from app.main import app
from app.routers.anime import get_provider

SUMMARY = AnimeSummary(
    mal_id=16498,
    title_english="Attack on Titan",
    title_jp="進撃の巨人",
    image="https://example.com/aot.jpg",
    score=8.5,
    episodes=25,
    year=2013,
    season="spring",
    status="Finished Airing",
    format="TV",
    genres=["Action", "Drama"],
    studios=["Wit Studio"],
)

CHARACTER = CharacterSummary(
    mal_id=40882,
    name="Eren Yeager",
    image="https://example.com/eren.jpg",
    role="Main",
)


class FakeProvider:
    def __init__(self, *, raise_not_found: bool = False, raise_upstream: bool = False):
        self.raise_not_found = raise_not_found
        self.raise_upstream = raise_upstream

    async def get_by_id(self, mal_id: int) -> AnimeSummary:
        if self.raise_not_found:
            raise AnimeNotFoundError(mal_id)
        if self.raise_upstream:
            raise UpstreamError("boom")
        return SUMMARY

    async def search(self, q: str, limit: int = 20) -> list[AnimeSummary]:
        if self.raise_upstream:
            raise UpstreamError("boom")
        return [SUMMARY]

    async def get_trending(self, limit: int = 20) -> list[AnimeSummary]:
        if self.raise_upstream:
            raise UpstreamError("boom")
        return [SUMMARY]

    async def get_seasonal(self, year: int, season: str, limit: int = 20) -> list[AnimeSummary]:
        if self.raise_upstream:
            raise UpstreamError("boom")
        return [SUMMARY]

    async def get_characters(self, mal_id: int) -> list[CharacterSummary]:
        if self.raise_not_found:
            raise AnimeNotFoundError(mal_id)
        if self.raise_upstream:
            raise UpstreamError("boom")
        return [CHARACTER]


def use_provider(provider: FakeProvider) -> None:
    app.dependency_overrides[get_provider] = lambda: provider


def teardown_function() -> None:
    app.dependency_overrides.clear()


client = TestClient(app)


def test_get_anime_success():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/16498")
    assert response.status_code == 200
    body = response.json()
    assert body["malId"] == 16498
    assert body["titleEnglish"] == "Attack on Titan"
    assert body["titleJp"] == "進撃の巨人"
    assert body["studios"] == ["Wit Studio"]


def test_get_anime_not_found():
    use_provider(FakeProvider(raise_not_found=True))
    response = client.get("/v1/anime/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_anime_invalid_mal_id():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/0")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"

    response = client.get("/v1/anime/not-a-number")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_get_anime_upstream_error():
    use_provider(FakeProvider(raise_upstream=True))
    response = client.get("/v1/anime/16498")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_search_anime_success():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/search", params={"q": "attack"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["malId"] == 16498


def test_search_anime_missing_q():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/search")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_search_anime_limit_out_of_range():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/search", params={"q": "attack", "limit": 100})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_trending_anime_success():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/trending")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["malId"] == 16498


def test_trending_anime_limit_out_of_range():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/trending", params={"limit": 100})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_trending_anime_upstream_error():
    use_provider(FakeProvider(raise_upstream=True))
    response = client.get("/v1/anime/trending")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_seasonal_anime_success():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/seasonal", params={"season": "summer", "year": 2025})
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["malId"] == 16498


def test_seasonal_anime_defaults_to_current_season():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/seasonal")
    assert response.status_code == 200
    assert response.json()["data"][0]["malId"] == 16498


def test_seasonal_anime_invalid_season():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/seasonal", params={"season": "bogus", "year": 2025})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_seasonal_anime_limit_out_of_range():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/seasonal", params={"season": "summer", "year": 2025, "limit": 100})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_seasonal_anime_upstream_error():
    use_provider(FakeProvider(raise_upstream=True))
    response = client.get("/v1/anime/seasonal", params={"season": "summer", "year": 2025})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_get_anime_characters_success():
    use_provider(FakeProvider())
    response = client.get("/v1/anime/16498/characters")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["malId"] == 40882
    assert body["data"][0]["name"] == "Eren Yeager"


def test_get_anime_characters_not_found():
    use_provider(FakeProvider(raise_not_found=True))
    response = client.get("/v1/anime/999999/characters")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
