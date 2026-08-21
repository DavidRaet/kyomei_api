from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import Settings
from app.rate_limit import build_limiter, rate_limit_exceeded_handler


def _build_test_app(*, per_minute: int, enabled: bool) -> FastAPI:
    settings = Settings(rate_limit_per_minute=per_minute, rate_limit_enabled=enabled)
    limiter = build_limiter(settings)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_requests_under_limit_succeed():
    client = TestClient(_build_test_app(per_minute=5, enabled=True))
    for _ in range(3):
        assert client.get("/ping").status_code == 200


def test_exceeding_limit_returns_429_with_error_envelope():
    client = TestClient(_build_test_app(per_minute=2, enabled=True))
    client.get("/ping")
    client.get("/ping")
    response = client.get("/ping")
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "rate_limited"
    assert "message" in body["error"]
    assert "retry-after" in response.headers


def test_disabled_limiter_never_blocks():
    client = TestClient(_build_test_app(per_minute=1, enabled=False))
    for _ in range(5):
        assert client.get("/ping").status_code == 200
