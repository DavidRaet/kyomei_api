import httpx
import pytest
import respx

from app.anilist.client import AniListClient
from app.anime.errors import AnimeNotFoundError, UpstreamError

ENDPOINT = "https://graphql.anilist.co"

MEDIA = {
    "idMal": 16498,
    "title": {"english": "Attack on Titan", "romaji": "Shingeki no Kyojin", "native": "進撃の巨人"},
    "coverImage": {"large": "https://example.com/aot.jpg"},
    "averageScore": 85,
    "episodes": 25,
    "seasonYear": 2013,
    "season": "SPRING",
    "status": "FINISHED",
    "format": "TV",
    "genres": ["Action", "Drama"],
    "studios": {"nodes": [{"name": "Wit Studio"}]},
}

DETAIL_MEDIA = {
    **MEDIA,
    "description": "Centuries ago, mankind was slaughtered...",
    "duration": 24,
    "startDate": {"year": 2013, "month": 4, "day": 7},
    "endDate": {"year": 2013, "month": 9, "day": 29},
    "trailer": {"thumbnail": "https://example.com/trailer.jpg"},
}

CHARACTER_EDGE = {
    "role": "MAIN",
    "node": {
        "id": 40882,
        "name": {"full": "Eren Yeager"},
        "image": {"large": "https://example.com/eren.jpg"},
        "favourites": 120000,
    },
    "voiceActors": [
        {
            "languageV2": "Japanese",
            "name": {"full": "Yuki Kaji"},
            "image": {"large": "https://example.com/kaji.jpg"},
        },
        {
            "languageV2": "English",
            "name": {"full": "Bryce Papenbrook"},
            "image": {"large": "https://example.com/bryce.jpg"},
        },
    ],
}


@pytest.fixture
async def client():
    async with AniListClient(endpoint=ENDPOINT) as c:
        yield c


@respx.mock
async def test_get_by_id_maps_fields(client):
    respx.post(ENDPOINT).respond(json={"data": {"Media": DETAIL_MEDIA}})

    detail = await client.get_by_id(16498)

    assert detail.mal_id == 16498
    assert detail.title_english == "Attack on Titan"
    assert detail.title_jp == "進撃の巨人"
    assert detail.title_romaji == "Shingeki no Kyojin"
    assert detail.score == 8.5
    assert detail.season == "spring"
    assert detail.status == "Finished Airing"
    assert detail.format == "TV"
    assert detail.studios == ["Wit Studio"]
    assert detail.synopsis == "Centuries ago, mankind was slaughtered..."
    assert detail.duration_minutes == 24
    assert detail.aired_from == "2013-04-07"
    assert detail.aired_to == "2013-09-29"
    assert detail.trailer_image == "https://example.com/trailer.jpg"


@respx.mock
async def test_get_by_id_title_falls_back_to_romaji_then_native(client):
    media = {**DETAIL_MEDIA, "title": {"english": None, "romaji": "Shingeki no Kyojin", "native": "進撃の巨人"}}
    respx.post(ENDPOINT).respond(json={"data": {"Media": media}})
    detail = await client.get_by_id(16498)
    assert detail.title_english == "Shingeki no Kyojin"
    assert detail.title_romaji == "Shingeki no Kyojin"

    media_native_only = {**DETAIL_MEDIA, "title": {"english": None, "romaji": None, "native": "進撃の巨人"}}
    respx.post(ENDPOINT).respond(json={"data": {"Media": media_native_only}})
    detail = await client.get_by_id(16498)
    assert detail.title_english == "進撃の巨人"
    assert detail.title_romaji is None


@respx.mock
async def test_get_by_id_not_found(client):
    respx.post(ENDPOINT).respond(json={"data": {"Media": None}})

    with pytest.raises(AnimeNotFoundError) as exc_info:
        await client.get_by_id(999999)

    assert exc_info.value.mal_id == 999999


@respx.mock
async def test_search_filters_entries_missing_mal_id(client):
    other = {**MEDIA, "idMal": None}
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": [MEDIA, other]}}})

    results = await client.search("attack")

    assert len(results) == 1
    assert results[0].mal_id == 16498


@respx.mock
async def test_get_trending_maps_list(client):
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": [MEDIA]}}})

    results = await client.get_trending()

    assert len(results) == 1
    assert results[0].mal_id == 16498


@respx.mock
async def test_get_seasonal_maps_list(client):
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": [MEDIA]}}})

    results = await client.get_seasonal(2013, "spring")

    assert len(results) == 1
    assert results[0].mal_id == 16498


@respx.mock
async def test_get_characters_maps_and_filters(client):
    edge_without_id = {"role": "SUPPORTING", "node": {"id": None, "name": {"full": "Nobody"}}}
    respx.post(ENDPOINT).respond(
        json={"data": {"Media": {"idMal": 16498, "characters": {"edges": [CHARACTER_EDGE, edge_without_id]}}}}
    )

    characters = await client.get_characters(16498)

    assert len(characters) == 1
    assert characters[0].mal_id == 40882
    assert characters[0].name == "Eren Yeager"
    assert characters[0].role == "Main"
    assert characters[0].favorites == 120000
    assert [va.name for va in characters[0].voice_actors] == ["Yuki Kaji", "Bryce Papenbrook"]
    assert characters[0].voice_actors[0].language == "Japanese"
    assert characters[0].voice_actors[0].image == "https://example.com/kaji.jpg"


@respx.mock
async def test_get_characters_defaults_missing_favorites_and_skips_nameless_vas(client):
    edge = {
        "role": "SUPPORTING",
        "node": {
            "id": 1,
            "name": {"full": "Someone"},
            "image": {"large": ""},
            "favourites": None,
        },
        "voiceActors": [
            {"languageV2": "Japanese", "name": {"full": None}, "image": {"large": ""}},
            {"languageV2": None, "name": {"full": "A Seiyuu"}, "image": None},
        ],
    }
    respx.post(ENDPOINT).respond(json={"data": {"Media": {"idMal": 16498, "characters": {"edges": [edge]}}}})

    characters = await client.get_characters(16498)

    assert characters[0].favorites == 0
    assert len(characters[0].voice_actors) == 1
    assert characters[0].voice_actors[0].name == "A Seiyuu"
    assert characters[0].voice_actors[0].language == "Unknown"
    assert characters[0].voice_actors[0].image == ""


@respx.mock
async def test_get_characters_not_found(client):
    respx.post(ENDPOINT).respond(json={"data": {"Media": None}})

    with pytest.raises(AnimeNotFoundError):
        await client.get_characters(999999)


@respx.mock
async def test_execute_timeout_raises_upstream_error(client):
    respx.post(ENDPOINT).mock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_connection_error_raises_upstream_error(client):
    respx.post(ENDPOINT).mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_malformed_json_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(content=b"not json", status_code=200)

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_http_500_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"errors": ["boom"]}, status_code=500)

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_http_400_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"errors": ["bad request"]}, status_code=400)

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_http_404_is_not_treated_as_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"data": {"Media": None}}, status_code=404)

    with pytest.raises(AnimeNotFoundError):
        await client.get_by_id(16498)


@respx.mock
async def test_execute_missing_data_key_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"errors": ["field error"]}, status_code=200)

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_search_with_errors_alongside_data_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": []}}, "errors": ["partial failure"]})

    with pytest.raises(UpstreamError):
        await client.search("attack")


@respx.mock
async def test_get_trending_with_errors_alongside_data_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": []}}, "errors": ["partial failure"]})

    with pytest.raises(UpstreamError):
        await client.get_trending()


@respx.mock
async def test_get_seasonal_with_errors_alongside_data_raises_upstream_error(client):
    respx.post(ENDPOINT).respond(json={"data": {"Page": {"media": []}}, "errors": ["partial failure"]})

    with pytest.raises(UpstreamError):
        await client.get_seasonal(2013, "spring")


@respx.mock
async def test_get_by_id_malformed_media_raises_upstream_error(client):
    malformed = {k: v for k, v in DETAIL_MEDIA.items() if k != "idMal"}
    respx.post(ENDPOINT).respond(json={"data": {"Media": malformed}})

    with pytest.raises(UpstreamError):
        await client.get_by_id(16498)


@respx.mock
async def test_get_by_id_partial_dates_and_missing_trailer_are_null(client):
    media = {
        **DETAIL_MEDIA,
        "description": None,
        "duration": None,
        "startDate": {"year": 2013, "month": 4, "day": None},
        "endDate": None,
        "trailer": None,
    }
    respx.post(ENDPOINT).respond(json={"data": {"Media": media}})

    detail = await client.get_by_id(16498)

    assert detail.synopsis is None
    assert detail.duration_minutes is None
    assert detail.aired_from is None
    assert detail.aired_to is None
    assert detail.trailer_image is None


@respx.mock
async def test_get_characters_malformed_edge_raises_upstream_error(client):
    malformed_edge = {"role": "MAIN", "node": {"id": {"not": "an int"}, "name": {"full": "Eren Yeager"}}}
    respx.post(ENDPOINT).respond(json={"data": {"Media": {"idMal": 16498, "characters": {"edges": [malformed_edge]}}}})

    with pytest.raises(UpstreamError):
        await client.get_characters(16498)
