# Wiring only: load config, create the FastAPI app, mount routers. No business logic here.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.anilist.client import AniListClient
from app.config import Settings
from app.routers.anime import router as anime_router
from app.routers.errors import register_exception_handlers

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.state.provider = AniListClient(settings.anilist_endpoint)
    yield
    await app.state.provider.aclose()


app = FastAPI(title="kyomei-api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(anime_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
