from pathlib import Path

from agent.markdown import format_exercise, save_lesson, slugify_title
from agent.models import BalletExercise, BalletLesson, ExerciseStep


def sample_exercise(title: str = "Tendu em quinta") -> BalletExercise:
    return BalletExercise(
        title=title,
        starting_position="Quinta posição",
        teacher_tips=["Mostrar bastante os braços"],
        steps=[
            ExerciseStep(
                order=1,
                action="Realizar tendu devant",
                counts="1 a 2",
                repetitions=2,
                legs_and_feet="Estender o pé à frente",
                arms="Segunda posição",
                head_and_torso="Cabeça para a direita",
                direction="Devant",
                notes=["Finalizar alongado"],
            ),
            ExerciseStep(order=2, action="Fechar em quinta"),
        ],
    )


def test_format_exercise_renders_vertical_presentation_and_timeline() -> None:
    result = format_exercise(sample_exercise())

    assert result.startswith("# Tendu em quinta\n")
    assert "**Posição inicial:** Quinta posição" in result
    assert "## Dicas da professora" in result
    assert "### 1. Realizar tendu devant" in result
    assert "- **Contagem:** 1 a 2" in result
    assert "- **Repetições:** 2" in result
    assert "- **Pernas e pés:** Estender o pé à frente" in result
    assert "- **Braços:** Segunda posição" in result
    assert "- **Cabeça e tronco:** Cabeça para a direita" in result
    assert "- **Direção:** Devant" in result
    assert "- **Observações:** Finalizar alongado" in result
    assert "## Linha do tempo" in result
    assert "```mermaid\nflowchart LR" in result
    assert 'S1["1. Realizar tendu devant<br/>Contagem: 1 a 2"]' in result
    assert "S1 --> S2" in result


def test_slugify_title_removes_accents_and_unsafe_characters() -> None:
    assert slugify_title("Pliés / Primeira posição") == "plies_primeira_posicao"
    assert slugify_title("!!!") == "exercicio"


def test_save_lesson_creates_one_file_per_exercise_and_ambiguities(
    tmp_path: Path,
) -> None:
    lesson = BalletLesson(
        exercises=[sample_exercise("Pliés"), sample_exercise("Pliés")],
        ambiguities=["A direção do segundo passo não ficou clara."],
    )

    paths = save_lesson(lesson, tmp_path / "output")

    assert [path.name for path in paths] == [
        "plies.md",
        "plies_2.md",
        "ambiguidades.md",
    ]
    assert "# Pliés" in paths[0].read_text(encoding="utf-8")
    assert paths[2].read_text(encoding="utf-8") == (
        "# Ambiguidades\n\n- A direção do segundo passo não ficou clara.\n"
    )


def test_exercise_named_ambiguidades_does_not_overwrite_special_file(
    tmp_path: Path,
) -> None:
    lesson = BalletLesson(
        exercises=[sample_exercise("Ambiguidades")],
        ambiguities=["Uma dúvida."],
    )

    paths = save_lesson(lesson, tmp_path)

    assert [path.name for path in paths] == ["ambiguidades_2.md", "ambiguidades.md"]
