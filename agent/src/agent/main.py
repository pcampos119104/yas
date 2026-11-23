import argparse
from collections.abc import Sequence
from pathlib import Path

from agent.agent import organize_transcription
from agent.config import Settings
from agent.markdown import save_lesson
from agent.models import BalletLesson
from agent.silverbullet import PublishedPage, create_publisher
from agent.transcription import transcribe_audio

OUTPUT_DIR = Path("output")


def run(audio_path: str | Path) -> BalletLesson:
    """Transcribe one audio file and organize its ballet exercises."""
    transcription = transcribe_audio(audio_path)
    return organize_transcription(transcription)


def publish_exercises(paths: list[Path]) -> list[PublishedPage]:
    """Publish exercise files when SilverBullet is configured."""
    publisher = create_publisher(Settings())
    if publisher is None:
        return []

    publisher.ensure_index()
    return [
        publisher.publish(path)
        for path in paths
        if path.name != "ambiguidades.md"
    ]


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
        lesson = run(args.audio)
        saved_paths = save_lesson(lesson, OUTPUT_DIR)
        published_pages = publish_exercises(saved_paths)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    if saved_paths:
        for path in saved_paths:
            print(f"Arquivo criado: {path}")
    else:
        print("Nenhum exercício ou ambiguidade pôde ser salvo.")

    for page in published_pages:
        print(f"Página publicada: {page.url}")


if __name__ == "__main__":
    main()
