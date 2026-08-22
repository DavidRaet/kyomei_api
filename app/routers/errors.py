from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.anime.errors import AnimeNotFoundError, UpstreamError, UpstreamUnavailableError
from app.routers.schemas import ErrorBody, ErrorResponse


async def not_found_handler(request: Request, exc: AnimeNotFoundError) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code="not_found", message=str(exc)))
    return JSONResponse(status_code=404, content=body.model_dump())


async def upstream_unavailable_handler(request: Request, exc: UpstreamUnavailableError) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code="upstream_unavailable",
            message="The anime data provider is temporarily unavailable. Please try again shortly.",
        )
    )
    return JSONResponse(status_code=503, content=body.model_dump())


async def upstream_error_handler(request: Request, exc: UpstreamError) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code="internal_error", message=str(exc)))
    return JSONResponse(status_code=500, content=body.model_dump())


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    field = ".".join(str(part) for part in first_error["loc"][1:])
    message = f"{field}: {first_error['msg']}" if field else first_error["msg"]
    body = ErrorResponse(error=ErrorBody(code="invalid_request", message=message))
    return JSONResponse(status_code=400, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AnimeNotFoundError, not_found_handler)
    app.add_exception_handler(UpstreamUnavailableError, upstream_unavailable_handler)
    app.add_exception_handler(UpstreamError, upstream_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
