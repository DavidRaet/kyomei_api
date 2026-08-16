"""Manual smoke test for app/jikan/client.py against the live Jikan API.

This is not part of the pytest suite (no mocking, hits the real network) —
it's a quick way to eyeball that the client still talks to Jikan correctly
after a change. Unit tests with mocked HTTP responses are tracked separately
under Section 5 of docs/fastapi-backend-setup-checklist.md.

Run from the repo root:

    uv run python scripts/smoke_test_jikan.py

No API key or .env setup required — Jikan's REST API is public.

Known flakiness: Jikan proxies live MyAnimeList data, and MAL itself is
intermittently unreachable. When that happens Jikan returns HTTP 504
("Jikan failed to connect to MyAnimeList") on any endpoint that needs a
fresh MAL fetch, while endpoints Jikan has cached (e.g. a prior get_by_id)
may still return 200. A 504 here surfaces as UpstreamError, which is
correct client behavior — it is not a bug in JikanClient. If this script
fails with UpstreamError mentioning "failed to connect to MyAnimeList",
re-run later rather than treating it as a regression; confirm independently
with e.g. `curl -s -o /dev/null -w '%{http_code}' https://api.jikan.moe/v4/anime/16498`.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.anime.errors import AnimeNotFoundError  # noqa: E402
from app.jikan.client import JikanClient  # noqa: E402


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    async with JikanClient() as client:
        anime = await client.get_by_id(16498)
        print("get_by_id:", anime)

        results = await client.search("Bleach")
        print("search count:", len(results))
        if results:
            print("first result:", results[0])

        characters = await client.get_characters(16498)
        print("characters count:", len(characters))
        if characters:
            print("first character:", characters[0])

        try:
            await client.get_by_id(999999999)
            print("ERROR: expected AnimeNotFoundError")
        except AnimeNotFoundError as exc:
            print("not-found case raised:", type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())
