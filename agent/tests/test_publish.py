from pathlib import Path
from unittest.mock import patch

from agent.publish import main
from agent.silverbullet import PageAlreadyExistsError, PublishedPage


def test_main_publishes_existing_markdown_and_skips_existing_pages(
    tmp_path: Path, capsys
) -> None:
    first = tmp_path / "adagio.md"
    second = tmp_path / "plies.md"
    ignored = tmp_path / "transcricao.txt"
    first.write_text("# Adagio\n", encoding="utf-8")
    second.write_text("# Pliés\n", encoding="utf-8")
    ignored.write_text("Transcrição", encoding="utf-8")

    with patch("agent.publish.create_publisher") as create_publisher:
        publisher = create_publisher.return_value
        publisher.publish.side_effect = [
            PublishedPage(first, "https://notes.example.com/ballet/aulas/adagio"),
            PageAlreadyExistsError("a página de pliés já existe"),
        ]
        main([str(tmp_path)])

    publisher.ensure_index.assert_called_once_with()
    assert [call.args[0] for call in publisher.publish.call_args_list] == [
        first,
        second,
    ]
    output = capsys.readouterr().out
    assert "Página publicada: https://notes.example.com/ballet/aulas/adagio" in output
    assert "Página ignorada: a página de pliés já existe" in output
