from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from agent.config import Settings
from agent.silverbullet import (
    PageAlreadyExistsError,
    SilverBulletPublisher,
    create_publisher,
)


def test_create_publisher_is_optional() -> None:
    settings = Settings(
        _env_file=None,
        silverbullet_url=None,
        silverbullet_token=None,
    )

    assert create_publisher(settings) is None


def test_create_publisher_rejects_partial_configuration() -> None:
    settings = Settings(
        _env_file=None,
        silverbullet_url="https://notes.example.com",
        silverbullet_token=None,
    )

    with pytest.raises(ValueError, match="SILVERBULLET_TOKEN"):
        create_publisher(settings)


def test_ensure_index_creates_dynamic_list() -> None:
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    response = MagicMock()
    response.__enter__.return_value = response

    with patch("agent.silverbullet.urlopen", return_value=response) as urlopen:
        publisher.ensure_index()

    request = urlopen.call_args.args[0]
    assert request.full_url == (
        "https://notes.example.com/.fs/ballet/aulas.md"
    )
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert request.get_header("If-none-match") == "*"
    content = request.data.decode()
    assert "# Aulas de balé" in content
    assert "^ballet/aulas/[^/]+$" in content


def test_ensure_index_accepts_an_existing_page() -> None:
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    error = HTTPError("url", 412, "Precondition Failed", {}, None)

    with patch("agent.silverbullet.urlopen", side_effect=error):
        publisher.ensure_index()


def test_publish_creates_page_and_returns_public_url(tmp_path: Path) -> None:
    local_path = tmp_path / "tendu_devant.md"
    local_path.write_text("# Tendu devant\n", encoding="utf-8")
    publisher = SilverBulletPublisher(
        "https://notes.example.com/",
        "secret-token",
        "/ballet/aulas/",
    )
    response = MagicMock()
    response.__enter__.return_value = response

    with patch("agent.silverbullet.urlopen", return_value=response) as urlopen:
        published = publisher.publish(local_path)

    request = urlopen.call_args.args[0]
    assert request.full_url == (
        "https://notes.example.com/.fs/ballet/aulas/tendu_devant.md"
    )
    assert request.data == b"# Tendu devant\n"
    assert published.url == (
        "https://notes.example.com/ballet/aulas/tendu_devant"
    )


def test_publish_does_not_overwrite_existing_page(tmp_path: Path) -> None:
    local_path = tmp_path / "plies.md"
    local_path.write_text("# Pliés\n", encoding="utf-8")
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    error = HTTPError("url", 412, "Precondition Failed", {}, None)

    with (
        patch("agent.silverbullet.urlopen", side_effect=error),
        pytest.raises(PageAlreadyExistsError, match="já existe"),
    ):
        publisher.publish(local_path)
