from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.database.session import get_database_session
from app.database.users import get_or_create_user_id
from app.routers.schemas import MeOut

router = APIRouter(prefix="/v1", tags=["auth"])


@router.get("/me", response_model=MeOut)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> MeOut:
    user_id = await get_or_create_user_id(session, current_user.external_identity_id)
    return MeOut(user_id=user_id)
