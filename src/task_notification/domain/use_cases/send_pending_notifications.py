"""Use case для отправки pending уведомлений."""

from task_notification.core.exceptions.notifications import NotificationSendError
from task_notification.core.logger import get_logger, log
from task_notification.infrastructure.email.email_service import EmailService
from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import (
    NotificationRepository,
    UserTelegramRepository,
)
from task_notification.infrastructure.telegram.notification_service import (
    TelegramNotificationService,
)
from task_notification.schemas.notification import (
    NotificationChannel,
    NotificationSchema,
    NotificationStatus,
    TaskNotificationMessage,
)


logger = get_logger(__name__)


class SendPendingNotificationsUseCase:
    """Use case для отправки всех pending уведомлений."""

    def __init__(
        self,
        database: Database,
        repository: NotificationRepository,
        user_telegram_repository: UserTelegramRepository,
        email_service: EmailService,
        telegram_service: TelegramNotificationService,
    ):
        self._database = database
        self._repository = repository
        self._user_telegram_repository = user_telegram_repository
        self._email_service = email_service
        self._telegram_service = telegram_service

    @log(logger)
    async def execute(self) -> dict:
        """Получить все pending уведомления и отправить их."""
        async with self._database.session() as session:
            pending = await self._repository.get_pending_notifications(session, limit=100)

        if not pending:
            logger.info("No pending notifications to send")
            return {"sent": 0, "failed": 0}

        logger.info(f"Found {len(pending)} pending notifications")

        sent_count = 0
        failed_count = 0

        for notification in pending:
            try:
                await self._send_notification(notification)

                async with self._database.session() as session:
                    await self._repository.update_notification_status(
                        session,
                        notification.id,
                        NotificationStatus.SENT,
                    )

                sent_count += 1
                logger.info(f"Notification {notification.id} sent successfully")

            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                logger.error(f"Failed to send notification {notification.id}: {error_msg}")

                try:
                    async with self._database.session() as session:
                        await self._repository.update_notification_status(
                            session,
                            notification.id,
                            NotificationStatus.FAILED,
                            error_message=error_msg,
                        )
                except Exception:
                    logger.exception(f"Failed to update notification {notification.id} status")

        logger.info(f"Sent {sent_count} notifications, {failed_count} failed")
        return {"sent": sent_count, "failed": failed_count}

    async def _send_notification(
        self,
        notification: NotificationSchema,
    ) -> None:
        """Отправить одно уведомление."""
        message = TaskNotificationMessage.model_validate_json(notification.message)

        if notification.notification_channel in (
            NotificationChannel.EMAIL,
            NotificationChannel.BOTH,
        ):
            await self._send_email_notification(
                notification=notification,
                message=message,
            )

        if notification.notification_channel in (
            NotificationChannel.TELEGRAM,
            NotificationChannel.BOTH,
        ):
            await self._send_telegram_notification(
                notification=notification,
                message=message,
            )

    async def _send_email_notification(
        self,
        notification: NotificationSchema,
        message: TaskNotificationMessage,
    ) -> None:
        """Отправить уведомление по email."""
        await self._email_service.send_task_notification(
            recipient=notification.recipient,
            task_id=message.task_id,
            task_title=message.task_title,
            task_description=message.task_description,
            event_type=message.event_type,
            task_status=message.status,
            task_priority=message.priority,
        )

    async def _send_telegram_notification(
        self,
        notification: NotificationSchema,
        message: TaskNotificationMessage,
    ) -> None:
        """Отправить уведомление по telegram."""
        async with self._database.session() as session:
            telegram_user = await self._user_telegram_repository.get_user_by_email(
                session=session,
                email=notification.recipient,
            )

        if telegram_user is None:
            raise NotificationSendError(
                notification_id=notification.id,
                detail=f"Telegram не зарегистрирован для пользователя {notification.recipient}",
            )

        await self._telegram_service.send_task_notification(
            telegram_id=telegram_user.telegram_id,
            task_id=message.task_id,
            task_title=message.task_title,
            task_description=message.task_description,
            event_type=message.event_type,
            task_status=message.status,
            task_priority=message.priority,
        )
