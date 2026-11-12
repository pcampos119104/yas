from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from agent.config import Settings
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS


def create_openai_model(settings: Settings) -> ChatOpenAI:
    """Create the configured OpenAI chat model."""
    api_key = settings.openai_api_key
    if api_key is None or not api_key.get_secret_value().strip():
        raise ValueError("OPENAI_API_KEY não foi configurada")

    return ChatOpenAI(
        api_key=api_key,
        model=settings.openai_model,
        temperature=settings.openai_temperature,
    )


def create_ballet_agent(
    settings: Settings | None = None,
    model: BaseChatModel | None = None,
) -> Any:
    """Create the single LangChain agent used by the application."""
    chat_model = model or create_openai_model(settings or Settings())
    return create_agent(
        model=chat_model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
