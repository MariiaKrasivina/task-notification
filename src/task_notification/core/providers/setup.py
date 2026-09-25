from typing import AsyncIterator
from aiogram import Bot
from dishka import Provider, Scope, make_async_container, make_container, provide

from task_notification.core.config import settings
from task_notification.core.providers.config_provider import ConfigProvider
from task_notification.domain.metrics.use_case import GetNotificationsMetricsUseCase
from task_notification.domain.use_cases.create_notification import CreateNotificationUseCase
from task_notification.domain.use_cases.get_notification_by_id import GetNotificationByIdUseCase
from task_notification.domain.use_cases.get_notifications import GetNotificationsUseCase
from task_notification.domain.use_cases.register_telegram_user import RegisterTelegramUserUseCase
from task_notification.domain.use_cases.send_pending_notifications import SendPendingNotificationsUseCase
from task_notification.domain.use_cases.update_notification_status import UpdateNotificationStatusUseCase
from task_notification.infrastructure.email.email_service import EmailService
from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import (
    NotificationRepository,
    UserTelegramRepository,
)
from task_notification.infrastructure.telegram.notification_service import TelegramNotificationService


# Config container для RabbitMQ
config_container = make_container(ConfigProvider())


class InfrastructureProvider(Provider):
    scope = Scope.APP

    @provide
    def get_database(self) -> Database:
        return Database(settings.postgres_url)

    @provide
    async def get_telegram_bot(self) -> AsyncIterator[Bot]:
        if settings.TELEGRAM_BOT_TOKEN is None:
            raise RuntimeError("Не указан токен Telegram-бота")

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN.get_secret_value())

        try:
            yield bot
        finally:
            await bot.session.close()


class RepositoryProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_notification_repository(self) -> NotificationRepository:
        return NotificationRepository()

    @provide
    def get_user_telegram_repository(self) -> UserTelegramRepository:
        return UserTelegramRepository()


class ServiceProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_email_service(self) -> EmailService:
        return EmailService()

    @provide
    def get_telegram_notification_service(
        self,
        bot: Bot,
    ) -> TelegramNotificationService:
        return TelegramNotificationService(bot=bot)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_create_notification(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> CreateNotificationUseCase:
        return CreateNotificationUseCase(database, repository)

    @provide
    def get_get_notification_by_id(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> GetNotificationByIdUseCase:
        return GetNotificationByIdUseCase(database, repository)

    @provide
    def get_update_notification_status(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> UpdateNotificationStatusUseCase:
        return UpdateNotificationStatusUseCase(database, repository)

    @provide
    def get_get_notifications(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> GetNotificationsUseCase:
        return GetNotificationsUseCase(database, repository)

    @provide
    def get_send_pending_notifications(
        self,
        database: Database,
        repository: NotificationRepository,
        email_service: EmailService,
    ) -> SendPendingNotificationsUseCase:
        return SendPendingNotificationsUseCase(database, repository, email_service)

    @provide
    def get_register_telegram_user(
        self,
        database: Database,
        repository: UserTelegramRepository,
    ) -> RegisterTelegramUserUseCase:
        return RegisterTelegramUserUseCase(database, repository)


class MetricsProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_notifications_metrics(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> GetNotificationsMetricsUseCase:
        return GetNotificationsMetricsUseCase(database, repository)


container = make_async_container(
    InfrastructureProvider(),
    RepositoryProvider(),
    ServiceProvider(),
    UseCaseProvider(),
    MetricsProvider(),
)
