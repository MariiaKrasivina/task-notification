import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from task_notification.core.config import settings


dispatcher = Dispatcher()


@dispatcher.message(CommandStart())
async def start_command(message: Message) -> None:
    await message.answer(
        "Привет! Я бот уведомлений о задачах. "
        "Скоро здесь можно будет привязать email."
    )


async def main() -> None:
    if not settings.TELEGRAM_BOT_ENABLED:
        raise RuntimeError("Telegram-бот отключён")

    if settings.TELEGRAM_BOT_TOKEN is None:
        raise RuntimeError("Не указан токен Telegram-бота")

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN.get_secret_value())
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())