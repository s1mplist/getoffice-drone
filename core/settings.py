from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

    # Core configs
    log_level: str = Field(default="DEBUG", description="Logging level", env="LOG_LEVEL")

    # Notion configs
    notion_token: str = Field(
        ...,
        description="Notion integration token",
        min_length=50,
        env="NOTION_TOKEN",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
