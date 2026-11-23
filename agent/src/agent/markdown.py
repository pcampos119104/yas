import re
import unicodedata
from pathlib import Path

from agent.models import BalletExercise, BalletLesson, ExerciseStep


def _append_optional(lines: list[str], label: str, value: object) -> None:
    if value is not None and value != "" and value != []:
        lines.append(f"- **{label}:** {value}")


def _format_step(step: ExerciseStep) -> list[str]:
    details: list[str] = []
    _append_optional(details, "Contagem", step.counts)
    _append_optional(details, "Repetições", step.repetitions)
    _append_optional(details, "Pernas e pés", step.legs_and_feet)
    _append_optional(details, "Braços", step.arms)
    _append_optional(details, "Cabeça e tronco", step.head_and_torso)
    _append_optional(details, "Direção", step.direction)
    if step.notes:
        _append_optional(details, "Observações", "; ".join(step.notes))

    lines = [f"### {step.order}. {step.action}"]
    if details:
        lines.extend(["", *details])
    return lines


def _mermaid_text(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("\n", " ")


def _format_timeline(steps: list[ExerciseStep]) -> list[str]:
    lines = ["## Linha do tempo", ""]
    if not steps:
        lines.append("Nenhum passo pôde ser identificado com segurança.")
        return lines

    lines.extend(["```mermaid", "flowchart TD"])
    for index, step in enumerate(steps, start=1):
        label = f"{step.order}. {_mermaid_text(step.action)}"
        if step.counts:
            label += f"<br/>Contagem: {_mermaid_text(step.counts)}"
        lines.append(f'    S{index}["{label}"]')
    if len(steps) > 1:
        node_ids = (f"S{index}" for index in range(1, len(steps) + 1))
        lines.append(f"    {' --> '.join(node_ids)}")
    lines.append("```")
    return lines


def format_exercise(exercise: BalletExercise) -> str:
    """Render one exercise as vertical Markdown with a Mermaid timeline."""
    lines = [f"# {exercise.title}"]
    if exercise.starting_position:
        lines.extend(["", f"**Posição inicial:** {exercise.starting_position}"])
    if exercise.teacher_tips:
        lines.extend(["", "## Dicas da professora", ""])
        lines.extend(f"- {tip}" for tip in exercise.teacher_tips)

    lines.extend(["", "## Sequência", ""])
    if exercise.steps:
        for index, step in enumerate(exercise.steps):
            if index > 0:
                lines.append("")
            lines.extend(_format_step(step))
    else:
        lines.append("Nenhum passo pôde ser identificado com segurança.")

    lines.extend(["", *_format_timeline(exercise.steps)])
    return "\n".join(lines).rstrip() + "\n"


def slugify_title(title: str) -> str:
    """Convert an exercise title to a safe, readable file stem."""
    normalized = unicodedata.normalize("NFKD", title)
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    slug = re.sub(r"[^a-z0-9]+", "_", without_accents.lower()).strip("_")
    return slug or "exercicio"


def _available_filename(
    title: str,
    used_names: set[str],
    filename_suffix: str | None = None,
) -> str:
    stem = slugify_title(title)
    suffix_text = f"-{filename_suffix}" if filename_suffix else ""
    filename = f"{stem}{suffix_text}.md"
    suffix = 2
    while filename in used_names:
        filename = f"{stem}_{suffix}{suffix_text}.md"
        suffix += 1
    used_names.add(filename)
    return filename


def format_ambiguities(ambiguities: list[str]) -> str:
    lines = ["# Ambiguidades", ""]
    lines.extend(f"- {ambiguity}" for ambiguity in ambiguities)
    return "\n".join(lines) + "\n"


def save_lesson(
    lesson: BalletLesson,
    output_dir: Path,
    *,
    filename_suffix: str | None = None,
) -> list[Path]:
    """Save each exercise and the lesson ambiguities as Markdown files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    used_names = {"ambiguidades.md"}

    for exercise in lesson.exercises:
        path = output_dir / _available_filename(
            exercise.title,
            used_names,
            filename_suffix,
        )
        path.write_text(format_exercise(exercise), encoding="utf-8")
        saved_paths.append(path)

    if lesson.ambiguities:
        path = output_dir / "ambiguidades.md"
        path.write_text(format_ambiguities(lesson.ambiguities), encoding="utf-8")
        saved_paths.append(path)

    return saved_paths
