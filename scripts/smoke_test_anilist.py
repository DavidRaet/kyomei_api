"""Manual smoke test for app/anilist/client.py against the live AniList API.

This is not part of the pytest suite (no mocking, hits the real network) —
it's a quick way to eyeball that the client still talks to AniList correctly
after a change. Unit tests with mocked HTTP responses are tracked separately
under Section 5 of docs/fastapi-backend-setup-checklist.md.

Run from the repo root:

    uv run python scripts/smoke_test_anilist.py

No API key or .env setup required — AniList's GraphQL endpoint is public.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.anilist.client import AniListClient  # noqa: E402
from app.anime.errors import AnimeNotFoundError  # noqa: E402


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    async with AniListClient() as client:
        anime = await client.get_by_id(16498)
        print("get_by_id:", anime)

        results = await client.search("Bleach: Thousand-Year Blood War Season 4")
        print("search count:", len(results))
        if results:
            print("first result:", results[0])

        characters = await client.get_characters(16498)
        print("characters count:", len(characters))
        if characters:
            print("first character:", characters[2])

        try:
            await client.get_by_id(999999999)
            print("ERROR: expected AnimeNotFoundError")
        except AnimeNotFoundError as exc:
            print("not-found case raised:", type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
