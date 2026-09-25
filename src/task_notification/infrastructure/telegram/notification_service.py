import re

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from task_notification.core.exceptions.base import BaseServiceException


class TelegramNotificationSendError(BaseServiceException):
    """Ошибка отправки уведомления в Telegram."""

    def __init__(
        self,
        telegram_id: int,
        error: str,
    ) -> None:
        super().__init__(f"Failed to send Telegram notification to {telegram_id}: {error}")


class TelegramNotificationService:
    """Сервис отправки уведомлений через Telegram Bot API."""

    _MARKDOWN_SPECIAL_CHARACTERS = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")

    def __init__(
        self,
        bot: Bot,
    ) -> None:
        self._bot = bot

    async def send_task_notification(
        self,
        telegram_id: int,
        task_id: int,
        task_title: str,
        task_description: str | None,
        event_type: str,
        task_status: str,
        task_priority: str,
    ) -> None:
        message = self._build_message(
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            event_type=event_type,
            task_status=task_status,
            task_priority=task_priority,
        )

        try:
            await self._bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
            )

        except TelegramAPIError as e:
            raise TelegramNotificationSendError(
                telegram_id=telegram_id,
                error=str(e),
            ) from e

    def _build_message(
        self,
        task_id: int,
        task_title: str,
        task_description: str | None,
        event_type: str,
        task_status: str,
        task_priority: str,
    ) -> str:
        event_labels = {
            "created": "Задача создана",
            "updated": "Задача обновлена",
            "deleted": "Задача удалена",
            "status_changed": "Статус задачи изменён",
            "assigned": "Назначен исполнитель",
        }

        event_label = event_labels.get(event_type, "Изменение задачи")

        lines = [
            f"*{self._escape_markdown(event_label)}*",
            "",
            f"*ID:* `{task_id}`",
            f"*Название:* {self._escape_markdown(task_title)}",
            f"*Описание:* {self._escape_markdown(task_description) if task_description is not None else 'Нет описания'}",
            f"*Статус:* {self._escape_markdown(task_status)}",
            f"*Приоритет:* {self._escape_markdown(task_priority)}",
        ]

        return "\n".join(lines)

    def _escape_markdown(self, value: str) -> str:
        return self._MARKDOWN_SPECIAL_CHARACTERS.sub(r"\\\1", value)