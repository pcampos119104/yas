from unittest.mock import patch

import pytest

from agent.agent import OPENROUTER_BASE_URL, create_openrouter_model
from agent.config import Settings


def test_settings_read_openrouter_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-provider/test-model")
    monkeypatch.setenv(
        "OPENROUTER_TRANSCRIPTION_MODEL", "test-provider/test-transcriber"
    )

    settings = Settings(_env_file=None)

    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "test-key"
    assert settings.openrouter_model == "test-provider/test-model"
    assert settings.openrouter_transcription_model == "test-provider/test-transcriber"


def test_model_uses_openrouter_endpoint() -> None:
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        openrouter_model="test-provider/test-model",
        openrouter_temperature=0.2,
    )

    with patch("agent.agent.ChatOpenAI") as chat_model:
        create_openrouter_model(settings)

    chat_model.assert_called_once_with(
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE_URL,
        model="test-provider/test-model",
        temperature=0.2,
    )


def test_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = Settings(_env_file=None, openrouter_api_key=None)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        create_openrouter_model(settings)
