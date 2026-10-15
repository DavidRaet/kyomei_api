from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AuthenticationConfigurationError, UnauthenticatedError
from app.auth.models import CurrentUser
from app.config import Settings
from app.database.session import get_database_session
from app.database.users import get_or_create_user_id


def create_clerk_client(settings: Settings) -> Clerk | None:
    if settings.clerk_secret_key is None:
        return None

    secret_key = settings.clerk_secret_key.get_secret_value()
    if not secret_key:
        return None
    return Clerk(bearer_auth=secret_key)


async def get_verified_external_identity(request: Request) -> str:
    clerk: Clerk | None = getattr(request.app.state, "clerk", None)
    if clerk is None or not settings_authorized_parties(request):
        raise AuthenticationConfigurationError

    request_state = clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=settings_authorized_parties(request),
            accepts_token=["session_token"],
        ),
    )
    external_identity_id = (
        request_state.payload.get("sub") if request_state.is_authenticated and request_state.payload else None
    )
    if not isinstance(external_identity_id, str) or not external_identity_id:
        raise UnauthenticatedError

    return external_identity_id


async def get_current_user(
    external_identity_id: str = Depends(get_verified_external_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CurrentUser:
    user_id = await get_or_create_user_id(session, external_identity_id)
    return CurrentUser(external_identity_id=external_identity_id, kyomei_user_id=user_id)


def settings_authorized_parties(request: Request) -> list[str]:
    settings: Settings = request.app.state.settings
    return settings.clerk_authorized_parties
