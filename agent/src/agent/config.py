from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "openai/gpt-4.1-mini"
    openrouter_temperature: float = 0.0
    openrouter_transcription_model: str = "openai/gpt-transcribe"
    transcription_timeout_seconds: float = 120.0
