from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import UserTelegramRepository
from task_notification.schemas.user_telegram import (
    UserTelegramCreate,
    UserTelegramSchema,
)


class RegisterTelegramUserUseCase:
    """Зарегистрировать или обновить привязку Telegram."""

    def __init__(
        self,
        database: Database,
        repository: UserTelegramRepository,
    ) -> None:
        self._database = database
        self._repository = repository

    async def execute(
        self,
        user: UserTelegramCreate,
    ) -> UserTelegramSchema:
        async with self._database.session() as session:
            registered_user = await self._repository.register_user(
                session=session,
                user=user,
            )

        return registered_user