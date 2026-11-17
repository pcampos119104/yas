from unittest.mock import patch

from agent.main import format_lesson, main
from agent.models import BalletExercise, BalletLesson, ExerciseStep


def sample_lesson() -> BalletLesson:
    return BalletLesson(
        exercises=[
            BalletExercise(
                title="Pliés",
                starting_position="Primeira posição",
                teacher_tips=[
                    "Mostrar bastante os braços",
                    "Movimentar mais a cabeça",
                ],
                steps=[
                    ExerciseStep(
                        order=1,
                        action="Realizar dois demi-pliés",
                        repetitions=2,
                        arms="Primeira posição no primeiro",
                    )
                ],
            )
        ],
        ambiguities=["A posição final dos braços não ficou clara."],
    )


def test_format_lesson_renders_exercise_and_ambiguities() -> None:
    result = format_lesson(sample_lesson())

    assert "## Pliés" in result
    assert "**Posição inicial:** Primeira posição" in result
    assert "1. Realizar dois demi-pliés" in result
    assert "**Repetições:** 2" in result
    assert "**Dicas da professora:**" in result
    assert "- Mostrar bastante os braços" in result
    assert "- Movimentar mais a cabeça" in result
    assert "## Ambiguidades" in result


def test_format_lesson_renders_each_exercise_separately() -> None:
    lesson = BalletLesson(
        exercises=[
            BalletExercise(
                title="Battement tendu",
                steps=[ExerciseStep(order=1, action="Realizar tendus à frente")],
            ),
            BalletExercise(
                title="En cloche",
                steps=[ExerciseStep(order=1, action="Realizar en cloche")],
            ),
        ]
    )

    result = format_lesson(lesson)

    assert "## Battement tendu" in result
    assert "## En cloche" in result


def test_main_prints_transcription_and_organized_lesson(capsys) -> None:
    with patch(
        "agent.main.run",
        return_value=("Faça dois demi-pliés.", sample_lesson()),
    ):
        main(["aula.ogg"])

    output = capsys.readouterr().out
    assert "# Transcrição" in output
    assert "Faça dois demi-pliés." in output
    assert "# Exercícios organizados" in output
    assert "## Pliés" in output
