from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    port: int = 8000
    anilist_endpoint: str = "https://graphql.anilist.co"
    cache_ttl_seconds: int = 300
    cors_allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "https://kyomei-0.vercel.app",
    ]

    model_config = {"env_file": ".env"}

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
