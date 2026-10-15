import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database.errors import DatabaseUnavailableError
from app.database.models import User
from app.database.session import create_database_engine, create_session_factory
from app.database.users import get_or_create_user_id


@pytest.mark.asyncio
async def test_user_lookup_maps_pool_timeout_to_database_unavailable():
    session = MagicMock(spec=AsyncSession)
    timeout = TimeoutError("Connection pool exhausted")
    session.scalar = AsyncMock(side_effect=timeout)

    with pytest.raises(DatabaseUnavailableError) as exc_info:
        await get_or_create_user_id(session, "user_verified")

    assert exc_info.value.__cause__ is timeout


@pytest.mark.asyncio
async def test_user_creation_is_stable_distinct_and_concurrency_safe(test_database_url):
    engine = create_database_engine(test_database_url)
    session_factory = create_session_factory(engine)
    first_clerk_id = f"user_test_{uuid4().hex}"
    second_clerk_id = f"user_test_{uuid4().hex}"

    async def resolve(clerk_user_id):
        async with session_factory() as session:
            return await get_current_user(clerk_user_id, session)

    try:
        first_ids = await asyncio.gather(*(resolve(first_clerk_id) for _ in range(5)))
        first_user = first_ids[0]
        first_id = first_user.kyomei_user_id
        assert first_user.external_identity_id == first_clerk_id
        assert first_ids == [first_user] * 5
        assert first_user == await resolve(first_clerk_id)
        assert first_id != (await resolve(second_clerk_id)).kyomei_user_id

        async with session_factory() as session:
            rows = (await session.scalars(select(User).where(User.clerk_user_id == first_clerk_id))).all()
            assert len(rows) == 1
            assert rows[0].id == first_id
            assert rows[0].created_at is not None
            assert rows[0].updated_at is not None
    finally:
        async with session_factory() as session:
            await session.execute(delete(User).where(User.clerk_user_id.in_([first_clerk_id, second_clerk_id])))
            await session.commit()
        await engine.dispose()
