# Wiring only: load config, create the FastAPI app, mount routers. No business logic here.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.anilist.client import AniListClient
from app.auth.dependencies import create_clerk_client
from app.config import Settings
from app.logging_config import configure_logging, log_requests
from app.rate_limit import register_rate_limiting
from app.routers.anime import router as anime_router
from app.routers.auth import router as auth_router
from app.routers.errors import register_exception_handlers

settings = Settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings.validate_production_auth()
    app.state.settings = settings
    app.state.provider = AniListClient(settings.anilist_endpoint)
    app.state.clerk = create_clerk_client(settings)
    yield
    await app.state.provider.aclose()


app = FastAPI(title="kyomei-api", lifespan=lifespan)

register_rate_limiting(app, settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)

register_exception_handlers(app)
app.include_router(anime_router)
app.include_router(auth_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
