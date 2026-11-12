from langchain_core.language_models import FakeListChatModel

from agent.agent import create_ballet_agent


def test_agent_returns_model_response() -> None:
    model = FakeListChatModel(responses=["Primeira posição."])

    ballet_agent = create_ballet_agent(model=model)
    result = ballet_agent.invoke(
        {"messages": [{"role": "user", "content": "Qual é a primeira posição?"}]}
    )

    assert result["messages"][-1].content == "Primeira posição."
