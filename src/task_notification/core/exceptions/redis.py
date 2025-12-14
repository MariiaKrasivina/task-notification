from typing import Final

from task_notification.core.exceptions.base import BaseServiceException


class RedisConnectionError(BaseServiceException):
    """Ошибка подключения к Redis."""

    _ERROR_MESSAGE_TEMPLATE: Final[str] = "Не удалось подключиться к Redis: {detail}"

    def __init__(self, detail: str) -> None:
        self.message = self._ERROR_MESSAGE_TEMPLATE.format(detail=detail)
        super().__init__(self.message)


class ARQJobError(BaseServiceException):
    """Ошибка ARQ задачи."""

    _ERROR_MESSAGE_TEMPLATE: Final[str] = "Ошибка выполнения задачи {job_name}: {detail}"

    def __init__(self, job_name: str, detail: str) -> None:
        self.message = self._ERROR_MESSAGE_TEMPLATE.format(job_name=job_name, detail=detail)
        super().__init__(self.message)

