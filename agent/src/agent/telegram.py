from __future__ import annotations

import asyncio
import contextlib
import logging
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.tracers.langchain import wait_for_all_tracers
from pydantic import ValidationError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agent.config import Settings
from agent.main import run
from agent.outbox import Outbox, PublishAttempt
from agent.transcription import SUPPORTED_AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)

CALLBACK_PREFIX = "yas:retry:"


class TelegramGateway:
    """Receive authorized audio and deliver it through the durable outbox."""

    def __init__(self, settings: Settings, outbox: Outbox | None = None) -> None:
        self.settings = settings
        self.outbox = outbox or Outbox(settings.outbox_dir)
        self._processing_lock = asyncio.Lock()
        self._publication_lock = asyncio.Lock()
        self._retry_task: asyncio.Task[None] | None = None

    def _is_authorized(self, update: Update | Any, context: Any) -> bool:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return False
        if chat.type not in {
            ChatType.PRIVATE,
            ChatType.GROUP,
            ChatType.SUPERGROUP,
        }:
            return False
        if chat.id != self.settings.telegram_allowed_chat_id:
            return False
        bot_id = getattr(context.bot, "id", None)
        if user.is_bot or user.id == bot_id:
            return False
        return user.id in self.settings.telegram_allowed_user_ids

    @staticmethod
    def _retry_markup(job_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Tentar novamente",
                        callback_data=f"{CALLBACK_PREFIX}{job_id}",
                    )
                ]
            ]
        )

    def _audio_details(self, message: Any) -> tuple[Any, str]:
        if message.voice is not None:
            return message.voice, ".ogg"

        media = message.audio or message.document
        if media is None:
            raise ValueError("nenhum áudio foi encontrado na mensagem")
        mime_type = (getattr(media, "mime_type", None) or "").lower()
        if message.document is not None and not mime_type.startswith("audio/"):
            raise ValueError("o documento enviado não é um áudio")

        extension = Path(getattr(media, "file_name", "") or "").suffix.lower()
        extension_aliases = {".oga": ".ogg", ".mpeg": ".mp3"}
        extension = extension_aliases.get(extension, extension)
        if not extension:
            extension = {
                "audio/ogg": ".ogg",
                "audio/mpeg": ".mp3",
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
            }.get(mime_type, "")
        if extension not in SUPPORTED_AUDIO_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            raise ValueError(f"formato não suportado; envie {supported}")
        return media, extension

    async def _download_audio(self, message: Any, context: Any, path: Path) -> None:
        media, _ = self._audio_details(message)
        file_size = getattr(media, "file_size", None)
        if file_size is not None and file_size > self.settings.telegram_max_audio_bytes:
            maximum_mb = self.settings.telegram_max_audio_bytes // (1024 * 1024)
            raise ValueError(f"o áudio excede o limite de {maximum_mb} MB")
        telegram_file = await context.bot.get_file(media.file_id)
        await telegram_file.download_to_drive(custom_path=path)

    async def _attempt(self, job_id: str) -> PublishAttempt:
        async with self._publication_lock:
            return await asyncio.to_thread(
                self.outbox.attempt_publish,
                job_id,
                self.settings,
            )

    @staticmethod
    def _success_text(attempt: PublishAttempt) -> str:
        if not attempt.pages:
            return "Publicação concluída no SilverBullet."
        links = "\n".join(page.url for page in attempt.pages)
        return f"Publicado no SilverBullet:\n{links}"

    @staticmethod
    def _ambiguities_text(ambiguities: list[str]) -> str:
        return "Ambiguidades identificadas:\n- " + "\n- ".join(ambiguities)

    async def handle_audio(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Download and process one authorized Telegram audio."""
        if not self._is_authorized(update, context):
            logger.debug("Ignored unauthorized Telegram audio")
            return
        message = update.effective_message
        chat = update.effective_chat
        if message is None or chat is None:
            return

        try:
            _, extension = self._audio_details(message)
        except ValueError as error:
            await message.reply_text(str(error))
            return

        await message.reply_text("Áudio recebido. Processando...")

        async with self._processing_lock:
            try:
                with tempfile.TemporaryDirectory(prefix="yas-telegram-") as directory:
                    audio_path = Path(directory) / f"audio{extension}"
                    await self._download_audio(message, context, audio_path)
                    lesson = await asyncio.to_thread(run, audio_path)

                job = await asyncio.to_thread(
                    self.outbox.create_job,
                    lesson,
                    telegram_chat_id=chat.id,
                    telegram_message_id=message.message_id,
                )
                if not job.files:
                    await asyncio.to_thread(
                        self.outbox.attempt_publish,
                        job.id,
                        self.settings,
                    )
                    await message.reply_text(
                        "O áudio foi processado, mas nenhum exercício pôde "
                        "ser identificado com segurança."
                    )
                    if job.ambiguities:
                        await message.reply_text(
                            self._ambiguities_text(job.ambiguities)
                        )
                    return

                attempt = await self._attempt(job.id)
                if attempt.complete:
                    await message.reply_text(self._success_text(attempt))
                else:
                    await message.reply_text(
                        "O exercício foi salvo, mas não foi possível publicar "
                        "no SilverBullet. Uma nova tentativa será feita "
                        "automaticamente.",
                        reply_markup=self._retry_markup(job.id),
                    )
                if job.ambiguities:
                    await message.reply_text(self._ambiguities_text(job.ambiguities))
            except (OSError, ValueError, RuntimeError):
                logger.exception("Failed to process Telegram audio")
                await message.reply_text("Não foi possível processar o áudio.")

    async def handle_retry(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Retry one durable publication selected through an inline button."""
        query = update.callback_query
        if query is None:
            return
        if not self._is_authorized(update, context):
            await query.answer()
            return
        data = query.data or ""
        job_id = data.removeprefix(CALLBACK_PREFIX)
        if not data.startswith(CALLBACK_PREFIX) or self.outbox.get_job(job_id) is None:
            await query.answer("Esta publicação não está mais pendente.")
            return

        await query.answer("Tentando publicar...")
        try:
            attempt = await self._attempt(job_id)
            if attempt.complete:
                await query.edit_message_text(self._success_text(attempt))
            else:
                await query.edit_message_text(
                    "O SilverBullet continua indisponível. O arquivo permanece "
                    "salvo e será tentado novamente.",
                    reply_markup=self._retry_markup(job_id),
                )
        except (OSError, ValueError, RuntimeError):
            logger.exception("Manual SilverBullet retry failed")
            await query.edit_message_text(
                "Não foi possível tentar a publicação. O arquivo permanece salvo.",
                reply_markup=self._retry_markup(job_id),
            )

    async def _retry_pending(self, application: Application) -> None:
        for job in await asyncio.to_thread(self.outbox.pending_jobs):
            try:
                attempt = await self._attempt(job.id)
                if attempt.complete:
                    await application.bot.send_message(
                        chat_id=job.telegram_chat_id,
                        text=self._success_text(attempt),
                    )
            except (OSError, ValueError, RuntimeError):
                logger.exception("Automatic retry failed for job %s", job.id)

    async def _retry_loop(self, application: Application) -> None:
        while True:
            await self._retry_pending(application)
            await asyncio.sleep(self.settings.telegram_retry_interval_seconds)

    async def initialize(self, application: Application) -> None:
        """Start automatic retries after Telegram initializes."""
        self._retry_task = asyncio.create_task(
            self._retry_loop(application),
            name="silverbullet-outbox-retry",
        )

    async def shutdown(self, _application: Application) -> None:
        if self._retry_task is None:
            return
        self._retry_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._retry_task


def build_application(settings: Settings) -> Application:
    """Build the single-process, audio-only Telegram application."""
    token = settings.telegram_bot_token
    if token is None or not token.get_secret_value().strip():
        raise ValueError("TELEGRAM_BOT_TOKEN não foi configurado")
    if settings.telegram_allowed_chat_id is None:
        raise ValueError("TELEGRAM_ALLOWED_CHAT_ID não foi configurado")
    if not settings.telegram_allowed_user_ids:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS não foi configurado")
    if settings.telegram_max_audio_bytes <= 0:
        raise ValueError("TELEGRAM_MAX_AUDIO_BYTES deve ser positivo")
    if settings.telegram_retry_interval_seconds <= 0:
        raise ValueError("TELEGRAM_RETRY_INTERVAL_SECONDS deve ser positivo")

    gateway = TelegramGateway(settings)
    application = (
        ApplicationBuilder()
        .token(token.get_secret_value())
        .concurrent_updates(False)
        .post_init(gateway.initialize)
        .post_stop(gateway.shutdown)
        .build()
    )
    audio_filter = filters.VOICE | filters.AUDIO | filters.Document.AUDIO
    application.add_handler(MessageHandler(audio_filter, gateway.handle_audio))
    application.add_handler(
        CallbackQueryHandler(
            gateway.handle_retry,
            pattern=rf"^{CALLBACK_PREFIX}[0-9a-z]{{6}}$",
        )
    )
    return application


def main() -> None:
    """Run the private audio bot with Telegram long polling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = Settings()
        application = build_application(settings)
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=False,
        )
    except (ValidationError, ValueError) as error:
        logger.error("Telegram bot startup failed: %s", error)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logger.exception("Telegram bot failed")
        raise SystemExit(1) from error
    finally:
        wait_for_all_tracers()


if __name__ == "__main__":
    main()
