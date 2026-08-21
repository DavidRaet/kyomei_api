from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import Settings
from app.routers.schemas import ErrorBody, ErrorResponse


def build_limiter(settings: Settings) -> Limiter:
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
        enabled=settings.rate_limit_enabled,
        headers_enabled=True,
    )


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code="rate_limited", message=f"Rate limit exceeded: {exc.detail}"))
    response = JSONResponse(status_code=429, content=body.model_dump())
    return request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)


def register_rate_limiting(app: FastAPI, settings: Settings) -> Limiter:
    limiter = build_limiter(settings)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    return limiter
