"""ARQ Worker для обработки фоновых задач отправки уведомлений."""

import asyncio

from arq import run_worker
from arq.connections import RedisSettings

from task_notification.core.config import settings
from task_notification.domain.tasks.send_notification import send_notification_task


class WorkerSettings:
    """Настройки ARQ Worker."""

    queue_name = settings.ARQ_QUEUE_NAME
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )
    allow_abort_jobs = True
    functions = [send_notification_task]


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))  # type: ignore
