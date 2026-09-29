from collections.abc import AsyncGenerator

from fastapi import Request
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def normalize_database_url(database_url: SecretStr | str) -> str:
    """Adapt Railway and standard PostgreSQL URLs for SQLAlchemy's psycopg dialect."""
    value = database_url.get_secret_value() if isinstance(database_url, SecretStr) else database_url
    if value.startswith("postgres://"):
        return f"postgresql+psycopg://{value.removeprefix('postgres://')}"
    if value.startswith("postgresql://"):
        return f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
    return value


def create_database_engine(database_url: SecretStr | str) -> AsyncEngine:
    return create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield a request-scoped database session for future protected endpoints."""
    session_factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "database_session_factory", None
    )
    if session_factory is None:
        raise RuntimeError("Database is not configured.")

    async with session_factory() as session:
        yield session
