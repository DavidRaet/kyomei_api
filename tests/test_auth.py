import asyncio
import logging
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.dependencies import get_current_user
from app.auth.errors import AuthenticationConfigurationError, UnauthenticatedError
from app.auth.models import CurrentUser
from app.config import Settings
from app.database.errors import DatabaseUnavailableError
from app.database.session import get_database_session
from app.main import app
from app.routers import auth as auth_router


class StubClerk:
    def __init__(self, request_state):
        self.request_state = request_state
        self.options = None

    def authenticate_request(self, request, options):
        self.options = options
        return self.request_state


def _request_with_auth_state(clerk, settings: Settings) -> Request:
    test_app = SimpleNamespace(state=SimpleNamespace(clerk=clerk, settings=settings))
    return Request({"type": "http", "method": "GET", "path": "/v1/me", "headers": [], "app": test_app})


def test_get_current_user_returns_verified_external_identity_and_session_only_options():
    request_state = SimpleNamespace(is_authenticated=True, payload={"sub": "user_verified"})
    clerk = StubClerk(request_state)
    request = _request_with_auth_state(clerk, Settings(clerk_authorized_parties=["http://localhost:5173"]))

    user = asyncio.run(get_current_user(request))

    assert user == CurrentUser(external_identity_id="user_verified")
    assert clerk.options.accepts_token == ["session_token"]
    assert clerk.options.authorized_parties == ["http://localhost:5173"]


@pytest.mark.parametrize(
    "request_state",
    [
        SimpleNamespace(is_authenticated=False, payload=None),
        SimpleNamespace(is_authenticated=True, payload={}),
        SimpleNamespace(is_authenticated=True, payload={"sub": 123}),
    ],
)
def test_get_current_user_rejects_unverified_or_missing_external_identity(request_state):
    request = _request_with_auth_state(
        StubClerk(request_state), Settings(clerk_authorized_parties=["http://localhost:5173"])
    )

    with pytest.raises(UnauthenticatedError):
        asyncio.run(get_current_user(request))


def test_get_current_user_fails_safely_without_auth_configuration():
    request = _request_with_auth_state(None, Settings())

    with pytest.raises(AuthenticationConfigurationError):
        asyncio.run(get_current_user(request))


def test_production_settings_require_clerk_configuration(monkeypatch):
    monkeypatch.delenv("CLERK_SECRET_KEY", raising=False)
    monkeypatch.delenv("CLERK_AUTHORIZED_PARTIES", raising=False)

    with pytest.raises(RuntimeError, match="CLERK_SECRET_KEY"):
        Settings(_env_file=None, environment="production").validate_production_auth()

    with pytest.raises(RuntimeError, match="CLERK_AUTHORIZED_PARTIES"):
        Settings(
            _env_file=None, environment="production", clerk_secret_key="sk_test_example"
        ).validate_production_auth()


def test_me_requires_authentication():
    def reject_request():
        raise UnauthenticatedError

    app.dependency_overrides[get_current_user] = reject_request
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthenticated", "message": "Authentication is required."}}


def test_me_returns_internal_user_id_for_verified_clerk_identity(monkeypatch):
    internal_id = UUID("0ec0a244-4481-4cfb-999c-700dcacbd15b")
    seen = []

    async def resolve_user(session, clerk_user_id):
        seen.append(clerk_user_id)
        return internal_id

    monkeypatch.setattr(auth_router, "get_or_create_user_id", resolve_user)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(external_identity_id="user_verified")
    app.dependency_overrides[get_database_session] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"userId": str(internal_id)}
    assert seen == ["user_verified"]


def test_me_returns_contract_error_when_database_is_unavailable():
    def unavailable():
        raise DatabaseUnavailableError

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(external_identity_id="user_verified")
    app.dependency_overrides[get_database_session] = unavailable
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "unavailable", "message": "The database is temporarily unavailable."}}


def test_authorization_header_is_not_logged(caplog, monkeypatch):
    async def resolve_user(session, clerk_user_id):
        return UUID("0ec0a244-4481-4cfb-999c-700dcacbd15b")

    monkeypatch.setattr(auth_router, "get_or_create_user_id", resolve_user)
    app.dependency_overrides[get_database_session] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(external_identity_id="user_verified")
    try:
        with TestClient(app) as client, caplog.at_level(logging.INFO, logger="kyomei_api"):
            response = client.get("/v1/me", headers={"Authorization": "Bearer secret-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "secret-token" not in caplog.text
