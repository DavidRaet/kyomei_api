"""Run a GraphQL query against AniList's public API with rate-limit backoff.

Usage:
    python query.py '<graphql query>' '<json variables>'

Public reads only — no auth/token handling. See ../SKILL.md for details.
"""

import json
import sys
import time

import httpx

ENDPOINT = "https://graphql.anilist.co"
MAX_ATTEMPTS = 5
FALLBACK_BACKOFF_SECONDS = 2.0


def run_query(query: str, variables: dict | None = None) -> dict:
    """POST a query+variables to AniList, retrying on 429 until it succeeds or gives up."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = httpx.post(
            ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        if response.status_code == 429:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"AniList rate limit exceeded after {MAX_ATTEMPTS} attempts")
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else FALLBACK_BACKOFF_SECONDS * attempt
            time.sleep(delay)
            continue

        response.raise_for_status()
        body = response.json()

        if "errors" in body:
            raise RuntimeError(f"AniList GraphQL error: {body['errors']}")

        return body["data"]

    raise RuntimeError("unreachable")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python query.py '<graphql query>' '<json variables>'", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    variables = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None

    data = run_query(query, variables)
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
