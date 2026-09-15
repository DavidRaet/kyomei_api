from fastapi import APIRouter, Depends

from app.auth.dependencies import require_auth
from app.auth.models import AuthenticatedUser
from app.routers.schemas import MeOut

router = APIRouter(prefix="/v1", tags=["auth"])


@router.get("/me", response_model=MeOut)
async def get_me(user: AuthenticatedUser = Depends(require_auth)) -> MeOut:
    return MeOut(user_id=user.user_id)
