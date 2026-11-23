import asyncio

from pydantic import ValidationError
from telegram import Bot
from telegram.error import TelegramError

from agent.config import Settings


async def check_connection(settings: Settings) -> str:
    """Call Telegram getMe and return a safe bot description."""
    token = settings.telegram_bot_token
    if token is None or not token.get_secret_value().strip():
        raise ValueError("TELEGRAM_BOT_TOKEN não foi configurado")

    async with Bot(token=token.get_secret_value()) as bot:
        user = await bot.get_me()
    username = f"@{user.username}" if user.username else user.full_name
    return f"{username} (ID {user.id})"


def main() -> None:
    try:
        description = asyncio.run(check_connection(Settings()))
    except (ValidationError, ValueError, TelegramError) as error:
        print(f"Falha na conexão com o Telegram: {error}")
        raise SystemExit(1) from error
    print(f"Conexão com o Telegram confirmada: {description}")


if __name__ == "__main__":
    main()
