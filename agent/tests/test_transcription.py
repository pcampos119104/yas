from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import OpenAIError

from agent.config import Settings
from agent.transcription import (
    TRANSCRIPTION_KEYWORDS,
    TRANSCRIPTION_LANGUAGES,
    TRANSCRIPTION_PROMPT,
    transcribe_audio,
    validate_audio_path,
)


def test_transcribe_audio_sends_ballet_context_and_preserves_text(
    tmp_path: Path,
) -> None:
    audio = tmp_path / "aula.ogg"
    audio.write_bytes(b"audio-data")
    client = Mock()
    client.audio.transcriptions.create.return_value = SimpleNamespace(
        text="  Dois demi-pliés.\n"
    )
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        openai_transcription_model="gpt-transcribe",
    )

    result = transcribe_audio(audio, settings=settings, client=client)

    assert result == "  Dois demi-pliés.\n"
    client.audio.transcriptions.create.assert_called_once()
    call = client.audio.transcriptions.create.call_args
    assert call.kwargs["model"] == "gpt-transcribe"
    assert call.kwargs["prompt"] == TRANSCRIPTION_PROMPT
    assert call.kwargs["keywords"] == TRANSCRIPTION_KEYWORDS
    assert call.kwargs["languages"] == TRANSCRIPTION_LANGUAGES
    assert "extra_body" not in call.kwargs
    assert Path(call.kwargs["file"].name) == audio
    assert call.kwargs["file"].closed


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


def test_transcribe_audio_requires_openai_key(tmp_path: Path) -> None:
    audio = tmp_path / "aula.wav"
    audio.write_bytes(b"audio")
    settings = Settings(_env_file=None, openai_api_key=None)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        transcribe_audio(audio, settings=settings, client=Mock())


def test_transcribe_audio_reports_api_error(tmp_path: Path) -> None:
    audio = tmp_path / "aula.mp3"
    audio.write_bytes(b"audio")
    client = Mock()
    client.audio.transcriptions.create.side_effect = OpenAIError("invalid audio")
    settings = Settings(_env_file=None, openai_api_key="test-key")

    with pytest.raises(RuntimeError, match="invalid audio"):
        transcribe_audio(audio, settings=settings, client=client)


def test_transcribe_audio_rejects_empty_api_response(tmp_path: Path) -> None:
    audio = tmp_path / "aula.wav"
    audio.write_bytes(b"audio")
    client = Mock()
    client.audio.transcriptions.create.return_value = SimpleNamespace(text="  \n")
    settings = Settings(_env_file=None, openai_api_key="test-key")

    with pytest.raises(RuntimeError, match="transcrição vazia"):
        transcribe_audio(audio, settings=settings, client=client)
