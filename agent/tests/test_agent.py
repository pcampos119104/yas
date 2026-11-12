from unittest.mock import Mock, patch

from agent.agent import create_ballet_agent, organize_transcription
from agent.models import BalletExercise, BalletLesson, ExerciseStep
from agent.prompts import SYSTEM_PROMPT


def test_agent_is_created_with_structured_response() -> None:
    model = Mock()

    with patch("agent.agent.create_agent", return_value="agent") as factory:
        result = create_ballet_agent(model=model)

    assert result == "agent"
    factory.assert_called_once()
    assert factory.call_args.kwargs["model"] is model
    assert factory.call_args.kwargs["response_format"] is BalletLesson
    assert "battement tendu" in SYSTEM_PROMPT


def test_organize_transcription_returns_structured_lesson() -> None:
    lesson = BalletLesson(
        exercises=[
            BalletExercise(
                name="Pliés",
                steps=[ExerciseStep(order=1, action="Dois demi-pliés")],
            )
        ]
    )
    ballet_agent = Mock()
    ballet_agent.invoke.return_value = {"structured_response": lesson}

    result = organize_transcription("Faça dois demi-pliés.", ballet_agent=ballet_agent)

    assert result == lesson
    message = ballet_agent.invoke.call_args.args[0]["messages"][0]["content"]
    assert "Faça dois demi-pliés." in message


def test_organize_transcription_rejects_empty_text() -> None:
    try:
        organize_transcription("  ", ballet_agent=Mock())
    except ValueError as error:
        assert "vazia" in str(error)
    else:
        raise AssertionError("empty transcription should fail")
