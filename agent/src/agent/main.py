import argparse
from collections.abc import Sequence
from pathlib import Path

from agent.agent import organize_transcription
from agent.models import BalletExercise, BalletLesson, ExerciseStep
from agent.transcription import transcribe_audio


def _append_optional(lines: list[str], label: str, value: object) -> None:
    if value is not None and value != "" and value != []:
        lines.append(f"   - **{label}:** {value}")


def _format_step(step: ExerciseStep) -> list[str]:
    lines = [f"{step.order}. {step.action}"]
    _append_optional(lines, "Contagem", step.counts)
    _append_optional(lines, "Repetições", step.repetitions)
    _append_optional(lines, "Pernas e pés", step.legs_and_feet)
    _append_optional(lines, "Braços", step.arms)
    _append_optional(lines, "Cabeça e tronco", step.head_and_torso)
    _append_optional(lines, "Direção", step.direction)
    if step.notes:
        _append_optional(lines, "Observações", "; ".join(step.notes))
    return lines


def _format_exercise(exercise: BalletExercise) -> list[str]:
    lines = [f"## {exercise.title}"]
    if exercise.starting_position:
        lines.append(f"**Posição inicial:** {exercise.starting_position}")
    if exercise.teacher_tips:
        lines.extend(["", "**Dicas da professora:**"])
        lines.extend(f"- {tip}" for tip in exercise.teacher_tips)
    lines.append("")
    if exercise.steps:
        for step in exercise.steps:
            lines.extend(_format_step(step))
    else:
        lines.append("Nenhum passo pôde ser identificado com segurança.")
    return lines


def format_lesson(lesson: BalletLesson) -> str:
    """Render a structured lesson as readable Markdown for the terminal."""
    lines: list[str] = ["# Exercícios organizados", ""]
    if lesson.exercises:
        for index, exercise in enumerate(lesson.exercises, start=1):
            if index > 1:
                lines.append("")
            lines.extend(_format_exercise(exercise))
    else:
        lines.append("Nenhum exercício pôde ser identificado com segurança.")

    if lesson.ambiguities:
        lines.extend(["", "## Ambiguidades"])
        lines.extend(f"- {ambiguity}" for ambiguity in lesson.ambiguities)
    return "\n".join(lines)


def run(audio_path: str | Path) -> tuple[str, BalletLesson]:
    """Transcribe one audio file and organize its ballet exercises."""
    transcription = transcribe_audio(audio_path)
    lesson = organize_transcription(transcription)
    return transcription, lesson


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcreve e organiza exercícios narrados de balé"
    )
    parser.add_argument(
        "audio",
        type=Path,
        help="arquivo de áudio no formato .ogg, .mp3 ou .wav",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        transcription, lesson = run(args.audio)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))

    print("# Transcrição")
    print()
    print(transcription)
    print()
    print(format_lesson(lesson))


if __name__ == "__main__":
    main()
