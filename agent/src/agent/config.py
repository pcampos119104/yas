from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_temperature: float = 0.0
    openai_transcription_model: str = "gpt-transcribe"
    transcription_timeout_seconds: float = 120.0
    silverbullet_url: str | None = None
    silverbullet_token: SecretStr | None = None
    silverbullet_publish_path: str = "ballet/aulas"

    @field_validator("silverbullet_url", "silverbullet_token", mode="before")
    @classmethod
    def empty_optional_values_are_none(cls, value: object) -> object:
        """Keep optional publication disabled when dotenv values are blank."""
        return None if value == "" else value
