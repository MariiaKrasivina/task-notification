from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "task-notification"
    ENV: str = "DEV"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8001
    ROOT_PATH: str = ""

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_SCHEMA: str = "task_notification"
    MIN_POOL_SIZE: int = 5
    MAX_POOL_SIZE: int = 10

    # RabbitMQ
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: SecretStr
    RABBITMQ_PASSWORD: SecretStr
    RABBITMQ_EXCHANGE: str = "tasks"
    RABBITMQ_QUEUE: str = "task.notifications"
    RABBITMQ_ROUTING_KEY: str = "task.notification"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # ARQ Settings
    ARQ_QUEUE_NAME: str = "arq:task_notifications"

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def rabbitmq_url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER.get_secret_value()}:{self.RABBITMQ_PASSWORD.get_secret_value()}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
        )

    @property
    def redis_settings(self) -> dict:
        """Настройки для ARQ."""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "database": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
        }


settings = Settings()

