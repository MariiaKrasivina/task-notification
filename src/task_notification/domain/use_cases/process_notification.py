from typing import Optional

from task_notification.core.logger import get_logger, log
from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import NotificationRepository
from task_notification.schemas.notification import (
    CreateNotification,
    NotificationSchema,
    NotificationStatus,
    NotificationType,
    TaskNotificationMessage,
)

logger = get_logger(__name__)


class ProcessNotificationUseCase:
    """Use case для обработки уведомлений."""

    def __init__(
        self,
        database: Database,
        repository: NotificationRepository,
    ):
        self._database = database
        self._repository = repository

    @log(logger)
    async def process_task_event(
        self,
        message: TaskNotificationMessage,
    ) -> NotificationSchema:
        """Обработать событие задачи и создать уведомление."""
        # Маппинг типов событий
        event_type_mapping = {
            "created": NotificationType.TASK_CREATED,
            "updated": NotificationType.TASK_UPDATED,
            "assigned": NotificationType.TASK_ASSIGNED,
            "status_changed": NotificationType.TASK_STATUS_CHANGED,
            "deleted": NotificationType.TASK_DELETED,
        }

        notification_type = event_type_mapping.get(
            message.event_type,
            NotificationType.TASK_UPDATED,
        )

        # Определяем получателя
        recipient = message.assignee or message.created_by

        # Формируем заголовок и сообщение
        title = f"Task {message.event_type}: {message.task_title}"
        notification_message = (
            f"Task '{message.task_title}' was {message.event_type}. "
            f"Status: {message.status}, Priority: {message.priority}"
        )

        notification = CreateNotification(
            task_id=message.task_id,
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=notification_message,
        )

        async with self._database.session() as session:
            created = await self._repository.create_notification(session, notification)

        logger.info(f"Notification created: id={created.id}, task_id={message.task_id}")
        return created

    @log(logger)
    async def get_by_id(self, notification_id: int) -> NotificationSchema:
        """Получить уведомление по ID."""
        async with self._database.session() as session:
            return await self._repository.get_one_notification(session, notification_id)

    @log(logger)
    async def update_status(
        self,
        notification_id: int,
        status: NotificationStatus,
        error_message: Optional[str] = None,
    ) -> NotificationSchema:
        """Обновить статус уведомления."""
        async with self._database.session() as session:
            return await self._repository.update_notification_status(
                session,
                notification_id,
                status,
                error_message,
            )
