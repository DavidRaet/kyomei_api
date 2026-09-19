from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import CurrentUser
from app.routers.schemas import MeOut

router = APIRouter(prefix="/v1", tags=["auth"])


@router.get("/me", response_model=MeOut)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(user_id=current_user.external_identity_id)
