from types import SimpleNamespace

import pytest
from telegram import Update

from agent.config import Settings
from agent.telegram import TelegramGateway, build_application


def telegram_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        telegram_bot_token="telegram-token",
        telegram_allowed_chat_id=123,
        telegram_allowed_user_ids=[456],
        outbox_dir=tmp_path / "outbox",
    )


def test_gateway_accepts_voice_and_supported_audio_files(tmp_path) -> None:
    gateway = TelegramGateway(telegram_settings(tmp_path))
    voice = SimpleNamespace(file_id="voice", file_size=10)
    audio = SimpleNamespace(
        file_id="audio",
        file_size=10,
        file_name="aula.mp3",
        mime_type="audio/mpeg",
    )

    assert gateway._audio_details(
        SimpleNamespace(voice=voice, audio=None, document=None)
    ) == (voice, ".ogg")
    assert gateway._audio_details(
        SimpleNamespace(voice=None, audio=audio, document=None)
    ) == (audio, ".mp3")


def test_gateway_rejects_unsupported_audio_extension(tmp_path) -> None:
    gateway = TelegramGateway(telegram_settings(tmp_path))
    audio = SimpleNamespace(
        file_id="audio",
        file_size=10,
        file_name="aula.m4a",
        mime_type="audio/mp4",
    )

    with pytest.raises(ValueError, match="formato não suportado"):
        gateway._audio_details(
            SimpleNamespace(voice=None, audio=audio, document=None)
        )


def test_build_application_ignores_text_and_accepts_voice(tmp_path) -> None:
    application = build_application(telegram_settings(tmp_path))
    message_handlers = [
        handler
        for handlers in application.handlers.values()
        for handler in handlers
        if handler.__class__.__name__ == "MessageHandler"
    ]

    assert len(message_handlers) == 1
    text_update = Update.de_json(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456, "is_bot": False, "first_name": "Ana"},
                "text": "Olá",
            },
        },
        application.bot,
    )
    voice_update = Update.de_json(
        {
            "update_id": 2,
            "message": {
                "message_id": 2,
                "date": 0,
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 456, "is_bot": False, "first_name": "Ana"},
                "voice": {
                    "file_id": "file",
                    "file_unique_id": "unique",
                    "duration": 1,
                },
            },
        },
        application.bot,
    )

    assert message_handlers[0].check_update(text_update) is False
    assert message_handlers[0].check_update(voice_update) is True
