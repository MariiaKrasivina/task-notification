import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from tenacity import before_sleep_log, retry, wait_exponential

from task_notification.core.config import settings
from task_notification.core.logger import get_logger
from task_notification.domain.metrics.registry_metrics import NOTIFICATIONS_RECEIVED
from task_notification.domain.use_cases.process_notification import ProcessNotificationUseCase
from task_notification.infrastructure.postgres.database import Database
from task_notification.infrastructure.postgres.repository import NotificationRepository
from task_notification.infrastructure.rabbitmq.config import RabbitMQConfig
from task_notification.schemas.notification import TaskNotificationMessage

logger = get_logger(__name__)


class RabbitMQConsumer:
    """Consumer для получения сообщений из RabbitMQ."""

    def __init__(self, rabbit_config: RabbitMQConfig):
        self.rabbit_config = rabbit_config
        self._database = Database(settings.postgres_url)
        self._repository = NotificationRepository()
        self._arq_redis: ArqRedis | None = None

    async def _get_arq_redis(self) -> ArqRedis:
        """Получить ArqRedis клиент."""
        if self._arq_redis is None:
            self._arq_redis = await create_pool(
                RedisSettings(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    database=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                )
            )
        return self._arq_redis

    async def handle_message(self, body: bytes) -> None:
        """Обработать сообщение из RabbitMQ."""
        try:
            data = json.loads(body.decode())
            message = TaskNotificationMessage.model_validate(data)

            logger.info(
                f"Received task event: task_id={message.task_id}, "
                f"event={message.event_type}"
            )

            NOTIFICATIONS_RECEIVED.inc()

            # Создаем use case
            use_case = ProcessNotificationUseCase(self._database, self._repository)

            # Создаем уведомление в БД
            notification = await use_case.process_task_event(message)

            # Ставим задачу на отправку в ARQ
            arq_redis = await self._get_arq_redis()
            await arq_redis.enqueue_job(
                "send_notification_task",
                notification.id,
            )

            logger.info(f"Task enqueued for notification {notification.id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.exception(f"Failed to process task event: {e}")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.ERROR),
    )
    async def run(self) -> None:
        """Запустить consumer."""
        connect_options = self.rabbit_config.get_connect_options()

        connection = await aio_pika.connect_robust(
            host=connect_options["host"],
            port=connect_options["port"],
            login=connect_options["login"],
            password=connect_options["password"],
        )

        logger.info(f"Connected to RabbitMQ: {self.rabbit_config.host}")

        async with connection:
            channel = await connection.channel()

            # Declare exchange
            exchange = await channel.declare_exchange(
                self.rabbit_config.exchange_name,
                ExchangeType.DIRECT,
                durable=True,
            )

            # Declare queue
            queue = await channel.declare_queue(
                self.rabbit_config.queue_name,
                durable=True,
            )

            # Bind queue to exchange
            await queue.bind(exchange, self.rabbit_config.routing_key)

            logger.info(
                f"Listening on queue '{self.rabbit_config.queue_name}' "
                f"with routing key '{self.rabbit_config.routing_key}'"
            )

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await self.handle_message(message.body)


async def get_rabbit_consumer() -> RabbitMQConsumer:
    """Создать RabbitMQ consumer."""
    return RabbitMQConsumer(rabbit_config=RabbitMQConfig())
