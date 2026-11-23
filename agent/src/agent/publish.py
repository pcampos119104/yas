import argparse
from collections.abc import Sequence
from pathlib import Path

from agent.config import Settings
from agent.silverbullet import PageAlreadyExistsError, create_publisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publica arquivos Markdown existentes no SilverBullet"
    )
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("output"),
        help="diretório com arquivos Markdown (padrão: output)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.directory.is_dir():
        parser.error(f"diretório não encontrado: {args.directory}")

    paths = sorted(args.directory.glob("*.md"))
    if not paths:
        parser.error(f"nenhum arquivo Markdown encontrado em {args.directory}")

    try:
        publisher = create_publisher(Settings())
        if publisher is None:
            parser.error(
                "configure SILVERBULLET_URL e SILVERBULLET_TOKEN para publicar"
            )
        publisher.ensure_index()

        for path in paths:
            try:
                page = publisher.publish(path)
            except PageAlreadyExistsError as error:
                print(f"Página ignorada: {error}")
            else:
                print(f"Página publicada: {page.url}")
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
