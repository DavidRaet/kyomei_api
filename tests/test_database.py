from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.config import Settings
from app.database.session import (
    create_database_engine,
    create_session_factory,
    get_database_session,
    normalize_database_url,
)


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        ("postgres://user:password@host:5432/kyomei", "postgresql+psycopg://user:password@host:5432/kyomei"),
        ("postgresql://user:password@host:5432/kyomei", "postgresql+psycopg://user:password@host:5432/kyomei"),
        (
            "postgresql+psycopg://user:password@host:5432/kyomei",
            "postgresql+psycopg://user:password@host:5432/kyomei",
        ),
    ],
)
def test_normalize_database_url(raw_url, expected_url):
    assert normalize_database_url(raw_url) == expected_url


def test_database_url_is_redacted_in_settings_representation():
    settings = Settings(_env_file=None, database_url="postgresql://user:db-password-value@localhost:5432/kyomei")

    assert "db-password-value" not in repr(settings)
    assert "SecretStr" in repr(settings)


def test_production_settings_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        environment="production",
        clerk_secret_key="sk_test_example",
        clerk_authorized_parties=["http://localhost:5173"],
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        settings.validate_production_database()


@pytest.mark.asyncio
async def test_database_session_dependency_yields_request_scoped_session():
    engine = create_database_engine("postgresql://user:password@host:5432/kyomei")
    session_factory = create_session_factory(engine)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database_session_factory=session_factory)))

    try:
        sessions = get_database_session(request)
        session = await anext(sessions)

        assert session.bind is engine
        await sessions.aclose()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_async_engine_connects_and_provides_sessions(database_url):
    engine = create_database_engine(SecretStr(database_url))
    session_factory = create_session_factory(engine)

    try:
        assert engine.pool._pre_ping is True
        async with session_factory() as session:
            assert await session.scalar(text("SELECT 1")) == 1
    finally:
        await engine.dispose()
