import base64
from pathlib import Path
from typing import Any

import httpx

from agent.config import Settings

OPENROUTER_TRANSCRIPTIONS_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
SUPPORTED_AUDIO_EXTENSIONS = frozenset({".mp3", ".ogg", ".wav"})


def validate_audio_path(audio_path: str | Path) -> Path:
    """Validate and normalize an audio path accepted by this version."""
    path = Path(audio_path).expanduser()
    if not path.is_file():
        raise ValueError(f"arquivo de áudio não encontrado: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise ValueError(
            f"formato de áudio não suportado: {extension or 'sem extensão'}; "
            f"use {supported}"
        )
    if path.stat().st_size == 0:
        raise ValueError(f"o arquivo de áudio está vazio: {path}")
    return path


def _response_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip() or "erro sem detalhes"

    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error or body)


def transcribe_audio(
    audio_path: str | Path,
    settings: Settings | None = None,
    client: Any | None = None,
) -> str:
    """Transcribe a ballet audio through OpenRouter's STT endpoint."""
    path = validate_audio_path(audio_path)
    current_settings = settings or Settings()
    api_key = current_settings.openrouter_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise ValueError("OPENROUTER_API_KEY não foi configurada")

    payload = {
        "model": current_settings.openrouter_transcription_model,
        "input_audio": {
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            "format": path.suffix.lower().removeprefix("."),
        },
        "language": "pt",
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }

    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=current_settings.transcription_timeout_seconds
    )
    try:
        response = http_client.post(
            OPENROUTER_TRANSCRIPTIONS_URL,
            headers=headers,
            json=payload,
        )
    except httpx.HTTPError as error:
        raise RuntimeError(
            f"não foi possível acessar a transcrição do OpenRouter: {error}"
        ) from error
    finally:
        if owns_client:
            http_client.close()

    if response.is_error:
        details = _response_error_message(response)
        raise RuntimeError(
            f"falha na transcrição do OpenRouter "
            f"(HTTP {response.status_code}): {details}"
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "o OpenRouter retornou uma resposta de transcrição inválida"
        ) from error

    text = data.get("text") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("o OpenRouter retornou uma transcrição vazia")
    return text.strip()
