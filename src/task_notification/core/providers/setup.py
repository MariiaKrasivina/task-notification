from dishka import Provider, Scope, make_async_container, make_container, provide

from task_notification.core.config import settings
from task_notification.core.providers.config_provider import ConfigProvider
from task_notification.domain.metrics.use_case import GetNotificationsMetricsUseCase
from task_notification.domain.use_cases.get_notifications import GetNotificationsUseCase
from task_notification.domain.use_cases.process_notification import ProcessNotificationUseCase
from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import NotificationRepository


# Config container для RabbitMQ
config_container = make_container(ConfigProvider())


class InfrastructureProvider(Provider):
    scope = Scope.APP

    @provide
    def get_database(self) -> Database:
        return Database(settings.postgres_url)


class RepositoryProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_notification_repository(self) -> NotificationRepository:
        return NotificationRepository()


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_process_notification(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> ProcessNotificationUseCase:
        return ProcessNotificationUseCase(database, repository)

    @provide
    def get_get_notifications(
        self,
        database: Database,
        repository: NotificationRepository,
    ) -> GetNotificationsUseCase:
        return GetNotificationsUseCase(database, repository)


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
    UseCaseProvider(),
    MetricsProvider(),
)
