from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

    # Core configs
    log_level: Literal["DEBUG", "INFO", "WARNING"] = Field(
        default="DEBUG", description="Logging level", env="LOG_LEVEL"
    )

    # Notion configs
    notion_token: str = Field(
        ...,
        description="Notion integration token",
        min_length=50,
        env="NOTION_TOKEN",
    )

    notion_database_id: str = Field(
        ...,
        description="Notion database ID",
        min_length=20,
        env="NOTION_DATABASE_ID",
    )

    # PDF service configs
    pdf_service_url: str = Field(
        default="/api/pdf/generate",
        description="URL do serviço de geração de PDF",
        env="PDF_SERVICE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
