"""Runtime configuration settings for the VedaAI Assessment Extractor."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_origins(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


CorsOrigins = Annotated[list[AnyHttpUrl], NoDecode, BeforeValidator(_parse_origins)]


class Settings(BaseSettings):
    """Runtime configuration. No external integration is required to start the API."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VedaAI Assessment Extractor API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: CorsOrigins = Field(default_factory=lambda: ["http://localhost:3000"])
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.6-flash"
    supabase_url: AnyHttpUrl | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_db_url: SecretStr | None = None
    supabase_question_papers_bucket: str = "question-papers"
    supabase_answer_sheets_bucket: str = "answer-sheets"
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0)

    # Shared demo key for mutating endpoints. Unset (the default) leaves them open, which is
    # what local development and the test suite rely on. Set it in the deployed environment
    # to gate the operations that cost Gemini quota or destroy data. It gates cost and
    # destruction, not identity - reads stay public so the demo can be explored freely.
    demo_access_key: SecretStr | None = None
    # Parses per client IP per hour. 0 disables the limit.
    parse_rate_limit_per_hour: int = Field(default=0, ge=0)

    @property
    def demo_access_key_required(self) -> bool:
        return self.demo_access_key is not None

    @property
    def gemini_is_configured(self) -> bool:
        return self.gemini_api_key is not None

    @property
    def supabase_is_configured(self) -> bool:
        return self.supabase_url is not None and self.supabase_service_role_key is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
