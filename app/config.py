from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    port: int = 8000
    anilist_endpoint: str = "https://graphql.anilist.co"
    cache_ttl_seconds: int = 300
    cors_allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "https://kyomei-0.vercel.app",
        "https://www.kyomei.link",
    ]
    rate_limit_per_minute: int = 60
    rate_limit_enabled: bool = True
    clerk_secret_key: SecretStr | None = None
    clerk_authorized_parties: Annotated[list[str], NoDecode] = []

    model_config = {"env_file": ".env"}

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("clerk_authorized_parties", mode="before")
    @classmethod
    def _split_clerk_authorized_parties(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def validate_production_auth(self) -> None:
        if self.environment != "production":
            return
        if self.clerk_secret_key is None or not self.clerk_secret_key.get_secret_value():
            raise RuntimeError("CLERK_SECRET_KEY must be configured in production.")
        if not self.clerk_authorized_parties:
            raise RuntimeError("CLERK_AUTHORIZED_PARTIES must be configured in production.")
