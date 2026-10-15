from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.errors import DatabaseUnavailableError
from app.database.models import User


async def get_or_create_user_id(session: AsyncSession, clerk_user_id: str) -> UUID:
    statement = (
        insert(User)
        .values(clerk_user_id=clerk_user_id)
        .on_conflict_do_nothing(constraint="uq_users_clerk_user_id")
        .returning(User.id)
    )
    try:
        async with session.begin():
            user_id = await session.scalar(statement)
            if user_id is None:
                user_id = await session.scalar(select(User.id).where(User.clerk_user_id == clerk_user_id))
            if user_id is None:
                raise RuntimeError("User lookup failed after insert conflict.")
            return user_id
    except OperationalError as exc:
        raise DatabaseUnavailableError from exc
