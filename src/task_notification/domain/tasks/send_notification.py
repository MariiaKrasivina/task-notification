"""ARQ задача для отправки уведомлений."""

from task_notification.core.exceptions.notifications import (
    NotificationNotFoundException,
    NotificationSendError,
)
from task_notification.core.exceptions.redis import ARQJobError
from task_notification.core.logger import get_logger, setup_logging
from task_notification.core.providers.setup import container
from task_notification.domain.metrics.registry_metrics import (
    NOTIFICATIONS_FAILED,
    NOTIFICATIONS_SENT,
)
from task_notification.domain.use_cases.process_notification import ProcessNotificationUseCase
from task_notification.schemas.notification import NotificationStatus

logger = get_logger(__name__)


async def send_notification_task(ctx: dict, notification_id: int) -> dict:
    """
    ARQ задача для отправки уведомления.
    
    В реальном проекте здесь была бы отправка email/push/telegram.
    Для учебного проекта просто логируем и обновляем статус.
    """
    setup_logging()
    logger.info(f"Processing notification {notification_id}")

    async with container() as scoped:
        use_case = await scoped.get(ProcessNotificationUseCase)

        try:
            notification = await use_case.get_by_id(notification_id)

            # Симулируем отправку
            logger.info(
                f"Sending notification: "
                f"type={notification.notification_type}, "
                f"recipient={notification.recipient}, "
                f"title={notification.title}"
            )

            # Обновляем статус
            await use_case.update_status(notification_id, NotificationStatus.SENT)
            NOTIFICATIONS_SENT.inc()

            logger.info(f"Notification {notification_id} sent successfully")
            return {"status": "success", "notification_id": notification_id}

        except NotificationNotFoundException as e:
            logger.error(str(e))
            NOTIFICATIONS_FAILED.inc()
            return {"status": "error", "message": str(e)}

        except Exception as e:
            error = NotificationSendError(notification_id, str(e))
            logger.exception(str(error))

            try:
                await use_case.update_status(
                    notification_id,
                    NotificationStatus.FAILED,
                    error_message=str(e),
                )
            except Exception:
                pass

            NOTIFICATIONS_FAILED.inc()
            raise ARQJobError("send_notification_task", str(e))
