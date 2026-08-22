from app.anime.models import AnimeDetail, AnimeSummary, CharacterSummary, VoiceActorSummary


def test_anime_detail_extends_summary_and_holds_extra_fields():
    detail = AnimeDetail(
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
        title_romaji="Shingeki no Kyojin",
        synopsis="Centuries ago...",
        duration_minutes=24,
        aired_from="2013-04-07",
        aired_to="2013-09-29",
        trailer_image="https://example.com/trailer.jpg",
    )
    assert isinstance(detail, AnimeSummary)
    assert detail.title_romaji == "Shingeki no Kyojin"
    assert detail.synopsis == "Centuries ago..."
    assert detail.duration_minutes == 24
    assert detail.aired_from == "2013-04-07"
    assert detail.aired_to == "2013-09-29"
    assert detail.trailer_image == "https://example.com/trailer.jpg"


def test_character_summary_requires_favorites_and_voice_actors():
    va = VoiceActorSummary(language="Japanese", name="Yuki Kaji", image="https://example.com/kaji.jpg")
    character = CharacterSummary(
        mal_id=40882,
        name="Eren Yeager",
        image="https://example.com/eren.jpg",
        role="Main",
        favorites=120000,
        voice_actors=[va],
    )
    assert character.favorites == 120000
    assert character.voice_actors[0].name == "Yuki Kaji"
