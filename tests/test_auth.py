import asyncio
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth.dependencies import require_auth
from app.auth.errors import AuthenticationConfigurationError, UnauthenticatedError
from app.auth.models import AuthenticatedUser
from app.config import Settings
from app.main import app


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


def test_require_auth_returns_verified_user_id_and_session_only_options():
    request_state = SimpleNamespace(is_authenticated=True, payload={"sub": "user_verified"})
    clerk = StubClerk(request_state)
    request = _request_with_auth_state(clerk, Settings(clerk_authorized_parties=["http://localhost:5173"]))

    user = asyncio.run(require_auth(request))

    assert user == AuthenticatedUser(user_id="user_verified")
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
def test_require_auth_rejects_unverified_or_missing_user_id(request_state):
    request = _request_with_auth_state(
        StubClerk(request_state), Settings(clerk_authorized_parties=["http://localhost:5173"])
    )

    with pytest.raises(UnauthenticatedError):
        asyncio.run(require_auth(request))


def test_require_auth_fails_safely_without_auth_configuration():
    request = _request_with_auth_state(None, Settings())

    with pytest.raises(AuthenticationConfigurationError):
        asyncio.run(require_auth(request))


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

    app.dependency_overrides[require_auth] = reject_request
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthenticated", "message": "Authentication is required."}}


def test_me_returns_dependency_verified_user_id():
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(user_id="user_verified")
    try:
        with TestClient(app) as client:
            response = client.get("/v1/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"userId": "user_verified"}


def test_authorization_header_is_not_logged(caplog):
    app.dependency_overrides[require_auth] = lambda: AuthenticatedUser(user_id="user_verified")
    try:
        with TestClient(app) as client, caplog.at_level(logging.INFO, logger="kyomei_api"):
            response = client.get("/v1/me", headers={"Authorization": "Bearer secret-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "secret-token" not in caplog.text
