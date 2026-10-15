import asyncio
import os
import sys

import pytest

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "")


def pytest_asyncio_loop_factories(config, item):
    return {"default": asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop}


@pytest.fixture
def test_database_url() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    return database_url
