from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from agent.config import Settings
from agent.silverbullet import (
    PageAlreadyExistsError,
    SilverBulletError,
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
    missing = HTTPError("url", 404, "Not Found", {}, None)

    with patch(
        "agent.silverbullet.urlopen",
        side_effect=[missing, response],
    ) as urlopen:
        publisher.ensure_index()

    existence_request = urlopen.call_args_list[0].args[0]
    assert existence_request.get_method() == "GET"
    assert existence_request.get_header("User-agent") == "YAS-Ballet-Agent/0.1"
    assert existence_request.get_header("X-sync-mode") == "true"

    request = urlopen.call_args_list[1].args[0]
    assert request.full_url == (
        "https://notes.example.com/.fs/ballet/aulas.md"
    )
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert request.get_header("If-none-match") == "*"
    assert request.get_header("X-sync-mode") == "true"
    content = request.data.decode()
    assert "# Aulas de balé" in content
    assert "^ballet/aulas/[^/]+$" in content


def test_ensure_index_accepts_an_existing_page() -> None:
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    response = MagicMock()
    response.__enter__.return_value = response

    with patch("agent.silverbullet.urlopen", return_value=response) as urlopen:
        publisher.ensure_index()

    assert urlopen.call_count == 1


def test_check_connection_accepts_missing_index_without_writing() -> None:
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    missing = HTTPError("url", 404, "Not Found", {}, None)

    with patch("agent.silverbullet.urlopen", side_effect=missing) as urlopen:
        publisher.check_connection()

    request = urlopen.call_args.args[0]
    assert request.get_method() == "GET"
    assert request.full_url == "https://notes.example.com/.fs/ballet/aulas.md"


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
    missing = HTTPError("url", 404, "Not Found", {}, None)

    with patch(
        "agent.silverbullet.urlopen",
        side_effect=[missing, response],
    ) as urlopen:
        published = publisher.publish(local_path)

    request = urlopen.call_args_list[1].args[0]
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
    response = MagicMock()
    response.__enter__.return_value = response

    with (
        patch("agent.silverbullet.urlopen", return_value=response) as urlopen,
        pytest.raises(PageAlreadyExistsError, match="já existe"),
    ):
        publisher.publish(local_path)

    assert urlopen.call_count == 1


def test_idempotent_publish_accepts_identical_existing_page(tmp_path: Path) -> None:
    local_path = tmp_path / "plies-01jabc.md"
    local_path.write_text("# Pliés\n", encoding="utf-8")
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b"# Pli\xc3\xa9s\n"

    with patch("agent.silverbullet.urlopen", return_value=response) as urlopen:
        published = publisher.publish_idempotent(local_path)

    assert urlopen.call_count == 1
    assert published.url == (
        "https://notes.example.com/ballet/aulas/plies-01jabc"
    )


def test_http_error_includes_response_details() -> None:
    publisher = SilverBulletPublisher(
        "https://notes.example.com",
        "secret-token",
        "ballet/aulas",
    )
    body = MagicMock()
    body.read.return_value = b"error code: 1010"
    error = HTTPError("url", 403, "Forbidden", {}, body)

    with (
        patch("agent.silverbullet.urlopen", side_effect=error),
        pytest.raises(SilverBulletError, match="error code: 1010"),
    ):
        publisher.ensure_index()
