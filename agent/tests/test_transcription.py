import base64
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent.config import Settings
from agent.transcription import (
    OPENROUTER_TRANSCRIPTIONS_URL,
    transcribe_audio,
    validate_audio_path,
)


class FakeResponse:
    def __init__(
        self,
        data: dict[str, object],
        status_code: int = 200,
    ) -> None:
        self._data = data
        self.status_code = status_code
        self.is_error = status_code >= 400
        self.text = ""

    def json(self) -> dict[str, object]:
        return self._data


def test_transcribe_audio_sends_ballet_context(tmp_path: Path) -> None:
    audio = tmp_path / "aula.ogg"
    audio.write_bytes(b"audio-data")
    client = Mock()
    client.post.return_value = FakeResponse({"text": "Dois demi-pliés."})
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        openrouter_transcription_model="openai/gpt-transcribe",
    )

    result = transcribe_audio(audio, settings=settings, client=client)

    assert result == "Dois demi-pliés."
    client.post.assert_called_once()
    call = client.post.call_args
    assert call.args[0] == OPENROUTER_TRANSCRIPTIONS_URL
    assert call.kwargs["headers"]["Authorization"] == "Bearer test-key"
    payload = call.kwargs["json"]
    assert payload["model"] == "openai/gpt-transcribe"
    assert payload["language"] == "pt"
    assert "keyterms" not in payload
    assert payload["input_audio"] == {
        "data": base64.b64encode(b"audio-data").decode("ascii"),
        "format": "ogg",
    }


@pytest.mark.parametrize("extension", [".ogg", ".mp3", ".wav", ".WAV"])
def test_validate_audio_path_accepts_supported_formats(
    tmp_path: Path, extension: str
) -> None:
    audio = tmp_path / f"aula{extension}"
    audio.write_bytes(b"audio")

    assert validate_audio_path(audio) == audio


def test_validate_audio_path_rejects_unsupported_format(tmp_path: Path) -> None:
    audio = tmp_path / "aula.m4a"
    audio.write_bytes(b"audio")

    with pytest.raises(ValueError, match="formato de áudio não suportado"):
        validate_audio_path(audio)


def test_transcribe_audio_requires_openrouter_key(tmp_path: Path) -> None:
    audio = tmp_path / "aula.wav"
    audio.write_bytes(b"audio")
    settings = Settings(_env_file=None, openrouter_api_key=None)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        transcribe_audio(audio, settings=settings, client=Mock())


def test_transcribe_audio_reports_api_error(tmp_path: Path) -> None:
    audio = tmp_path / "aula.mp3"
    audio.write_bytes(b"audio")
    client = Mock()
    client.post.return_value = FakeResponse(
        {"error": {"message": "invalid audio"}}, status_code=400
    )
    settings = Settings(_env_file=None, openrouter_api_key="test-key")

    with pytest.raises(RuntimeError, match="invalid audio"):
        transcribe_audio(audio, settings=settings, client=client)
