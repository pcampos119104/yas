from pathlib import Path
from unittest.mock import patch

from agent.main import main, publish_exercises
from agent.models import BalletExercise, BalletLesson, ExerciseStep


def sample_lesson() -> BalletLesson:
    return BalletLesson(
        exercises=[
            BalletExercise(
                title="Pliés",
                starting_position="Primeira posição",
                steps=[ExerciseStep(order=1, action="Realizar dois demi-pliés")],
            )
        ],
        ambiguities=["A posição final dos braços não ficou clara."],
    )


def test_main_saves_markdown_files_and_prints_their_paths(
    tmp_path: Path, capsys
) -> None:
    output_dir = tmp_path / "output"
    with (
        patch("agent.main.run", return_value=sample_lesson()),
        patch("agent.main.OUTPUT_DIR", output_dir),
        patch("agent.main.publish_exercises", return_value=[]),
    ):
        main(["aula.ogg"])

    output = capsys.readouterr().out
    assert f"Arquivo criado: {output_dir / 'plies.md'}" in output
    assert f"Arquivo criado: {output_dir / 'ambiguidades.md'}" in output
    assert (output_dir / "plies.md").is_file()
    assert (output_dir / "ambiguidades.md").is_file()


def test_publish_exercises_skips_ambiguities(tmp_path: Path) -> None:
    exercise_path = tmp_path / "plies.md"
    ambiguity_path = tmp_path / "ambiguidades.md"
    with patch("agent.main.create_publisher") as create_publisher:
        client = create_publisher.return_value
        publish_exercises([exercise_path, ambiguity_path])

    client.ensure_index.assert_called_once_with()
    client.publish.assert_called_once_with(exercise_path)
