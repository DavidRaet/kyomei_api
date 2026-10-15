import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.auth.dependencies import get_current_user, get_verified_external_identity
from app.auth.errors import AuthenticationConfigurationError, UnauthenticatedError
from app.auth.models import CurrentUser
from app.config import Settings
from app.database.errors import DatabaseUnavailableError
from app.database.session import get_database_session
from app.main import app
from app.routers.anime import get_provider


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


def test_verification_returns_external_identity_and_session_only_options():
    request_state = SimpleNamespace(is_authenticated=True, payload={"sub": "user_verified"})
    clerk = StubClerk(request_state)
    request = _request_with_auth_state(clerk, Settings(clerk_authorized_parties=["http://localhost:5173"]))

    identity = asyncio.run(get_verified_external_identity(request))

    assert identity == "user_verified"
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
def test_verification_rejects_unverified_or_missing_external_identity(request_state):
    request = _request_with_auth_state(
        StubClerk(request_state), Settings(clerk_authorized_parties=["http://localhost:5173"])
    )

    with pytest.raises(UnauthenticatedError):
        asyncio.run(get_verified_external_identity(request))


def test_verification_fails_safely_without_auth_configuration():
    request = _request_with_auth_state(None, Settings())

    with pytest.raises(AuthenticationConfigurationError):
        asyncio.run(get_verified_external_identity(request))


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


def test_me_returns_current_user_id_without_clerk_or_database():
    internal_id = UUID("0ec0a244-4481-4cfb-999c-700dcacbd15b")
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        external_identity_id="user_verified", kyomei_user_id=internal_id
    )
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"userId": str(internal_id)}


@pytest.fixture
def verified_client(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state, "clerk", StubClerk(SimpleNamespace(is_authenticated=True, payload={"sub": "user_verified"}))
        )
        monkeypatch.setattr(app.state, "settings", Settings(clerk_authorized_parties=["http://localhost:5173"]))
        yield client


def test_me_returns_contract_error_when_database_is_unavailable(verified_client):
    def unavailable():
        raise DatabaseUnavailableError

    app.dependency_overrides[get_database_session] = unavailable
    try:
        response = verified_client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "unavailable", "message": "The database is temporarily unavailable."}}


def test_current_user_resolves_verified_identity(verified_client):
    internal_id = UUID("0ec0a244-4481-4cfb-999c-700dcacbd15b")
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=internal_id)
    app.dependency_overrides[get_database_session] = lambda: session
    try:
        response = verified_client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"userId": str(internal_id)}


@pytest.mark.parametrize("error", [TimeoutError("pool exhausted"), OperationalError("connect", {}, Exception())])
def test_current_user_maps_database_failures_to_503(verified_client, error):
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=error)
    app.dependency_overrides[get_database_session] = lambda: session
    try:
        response = verified_client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"error": {"code": "unavailable", "message": "The database is temporarily unavailable."}}


@pytest.mark.parametrize(
    "request_state",
    [
        SimpleNamespace(is_authenticated=False, payload=None),
        SimpleNamespace(is_authenticated=True, payload={}),
        SimpleNamespace(is_authenticated=True, payload={"sub": 123}),
        SimpleNamespace(is_authenticated=True, payload={"sub": ""}),
    ],
)
def test_invalid_session_never_acquires_database_session(verified_client, monkeypatch, request_state):
    monkeypatch.setattr(app.state, "clerk", StubClerk(request_state))

    def unexpected_database_access():
        pytest.fail("Invalid authentication must be rejected before database access")

    app.dependency_overrides[get_database_session] = unexpected_database_access
    try:
        response = verified_client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthenticated", "message": "Authentication is required."}}


@pytest.mark.parametrize("path", ["/health", "/v1/anime/search?q=naruto"])
def test_public_routes_do_not_require_authentication_or_database(path):
    def unexpected_dependency():
        pytest.fail("Public routes must not require authentication or a database")

    app.dependency_overrides[get_current_user] = unexpected_dependency
    app.dependency_overrides[get_database_session] = unexpected_dependency
    app.dependency_overrides[get_provider] = lambda: SimpleNamespace(search=AsyncMock(return_value=[]))
    try:
        with TestClient(app) as client:
            response = client.get(path)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_authorization_header_is_not_logged(caplog):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        external_identity_id="user_verified", kyomei_user_id=UUID("0ec0a244-4481-4cfb-999c-700dcacbd15b")
    )
    try:
        with TestClient(app) as client, caplog.at_level(logging.INFO, logger="kyomei_api"):
            response = client.get("/v1/me", headers={"Authorization": "Bearer secret-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "secret-token" not in caplog.text
