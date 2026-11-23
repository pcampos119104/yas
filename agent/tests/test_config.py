from unittest.mock import patch

import pytest

from agent.agent import create_openai_model
from agent.config import Settings


def test_settings_read_api_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_TRANSCRIPTION_MODEL", "test-transcriber")
    monkeypatch.setenv("SILVERBULLET_URL", "https://notes.example.com")
    monkeypatch.setenv("SILVERBULLET_TOKEN", "silverbullet-test-token")
    monkeypatch.setenv("SILVERBULLET_PUBLISH_PATH", "ballet/aulas")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "openai-test-key"
    assert settings.openai_model == "test-model"
    assert settings.openai_temperature == 0.2
    assert settings.openai_transcription_model == "test-transcriber"
    assert settings.silverbullet_url == "https://notes.example.com"
    assert settings.silverbullet_token is not None
    assert (
        settings.silverbullet_token.get_secret_value() == "silverbullet-test-token"
    )
    assert settings.silverbullet_publish_path == "ballet/aulas"


def test_model_uses_openai_configuration() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        openai_model="gpt-4.1-mini",
        openai_temperature=0.2,
    )

    with patch("agent.agent.ChatOpenAI") as chat_model:
        create_openai_model(settings)

    chat_model.assert_called_once_with(
        api_key=settings.openai_api_key,
        model="gpt-4.1-mini",
        temperature=0.2,
    )


def test_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None, openai_api_key=None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_openai_model(settings)


def test_empty_silverbullet_environment_disables_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SILVERBULLET_URL", "")
    monkeypatch.setenv("SILVERBULLET_TOKEN", "")

    settings = Settings(_env_file=None)

    assert settings.silverbullet_url is None
    assert settings.silverbullet_token is None
