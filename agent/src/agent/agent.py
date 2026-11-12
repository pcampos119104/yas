from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent.config import Settings
from agent.models import BalletLesson
from agent.prompts import SYSTEM_PROMPT, TRANSCRIPTION_MESSAGE
from agent.tools import TOOLS

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def create_openrouter_model(settings: Settings) -> ChatOpenAI:
    """Create the configured OpenRouter chat model."""
    api_key = settings.openrouter_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise ValueError("OPENROUTER_API_KEY não foi configurada")

    return ChatOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        model=settings.openrouter_model,
        temperature=settings.openrouter_temperature,
    )


def create_ballet_agent(
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
) -> Any:
    """Create the single LangChain agent used by the application."""
    chat_model = model or create_openrouter_model(settings or Settings())
    return create_agent(
        model=chat_model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=BalletLesson,
    )


def organize_transcription(
    transcription: str,
    settings: Settings | None = None,
    ballet_agent: Any | None = None,
) -> BalletLesson:
    """Turn a raw transcript into faithful, structured ballet exercises."""
    if not transcription.strip():
        raise ValueError("a transcrição não pode estar vazia")

    current_agent = ballet_agent or create_ballet_agent(settings=settings)
    try:
        result = current_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": TRANSCRIPTION_MESSAGE.format(
                            transcription=transcription
                        ),
                    }
                ]
            }
        )
    except Exception as error:
        raise RuntimeError(
            f"não foi possível organizar a transcrição: {error}"
        ) from error

    structured_response = result.get("structured_response")
    if isinstance(structured_response, BalletLesson):
        return structured_response
    try:
        return BalletLesson.model_validate(structured_response)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "o agente não retornou um exercício estruturado válido"
        ) from error
