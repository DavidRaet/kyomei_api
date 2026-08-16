from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8000
    anilist_endpoint: str = "https://graphql.anilist.co"
    cache_ttl_seconds: int = 300

    model_config = {"env_file": ".env"}
