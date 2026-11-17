from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError

from agent.config import Settings

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".mp3", ".ogg", ".wav"})
TRANSCRIPTION_PROMPT = (
    "O áudio contém instruções de uma professora de balé clássico em português "
    "brasileiro, com terminologia técnica francesa de balé."
)
TRANSCRIPTION_KEYWORDS = (
    "battement tendu",
    "demi-plié",
    "grand plié",
    "en croix",
    "en cloche",
    "devant",
    "derrière",
    "à la seconde",
    "relevé",
    "passé",
    "rond de jambe",
)
TRANSCRIPTION_LANGUAGES = ("pt", "fr")


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


def transcribe_audio(
    audio_path: str | Path,
    settings: Settings | None = None,
    client: Any | None = None,
) -> str:
    """Transcribe a ballet audio through OpenAI's official API."""
    path = validate_audio_path(audio_path)
    current_settings = settings or Settings()
    api_key = current_settings.openai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise ValueError("OPENAI_API_KEY não foi configurada")

    owns_client = client is None
    openai_client = client or OpenAI(
        api_key=api_key.get_secret_value(),
        timeout=current_settings.transcription_timeout_seconds,
    )
    try:
        with path.open("rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                model=current_settings.openai_transcription_model,
                file=audio_file,
                prompt=TRANSCRIPTION_PROMPT,
                keywords=TRANSCRIPTION_KEYWORDS,
                languages=TRANSCRIPTION_LANGUAGES,
            )
    except OpenAIError as error:
        raise RuntimeError(
            f"não foi possível transcrever o áudio pela OpenAI: {error}"
        ) from error
    finally:
        if owns_client:
            openai_client.close()

    text = getattr(transcription, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("a OpenAI retornou uma transcrição vazia")
    return text
