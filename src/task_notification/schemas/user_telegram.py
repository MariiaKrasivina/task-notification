from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserTelegramCreate(BaseModel):
    """Данные для регистрации Telegram-пользователя."""

    email: EmailStr = Field(max_length=255)
    telegram_id: int
    telegram_username: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Нормализовать email перед сохранением."""

        return value.strip().lower()


class UserTelegramSchema(UserTelegramCreate):
    """Привязка Telegram-пользователя из базы."""

    model_config = ConfigDict(from_attributes=True)

    registered_at: datetime