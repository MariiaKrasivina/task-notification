import json
from dataclasses import dataclass
from enum import StrEnum
from hmac import compare_digest

from redis.asyncio import Redis
from redis.exceptions import WatchError


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"
    NO_ACTIVE_CODE = "no_active_code"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    email: str | None = None


class TelegramRegistrationStore:
    """Хранилище для сообщений подтверждения регистрации пользователей Telegram."""

    CODE_TTL_SECONDS = 600
    MAX_ATTEMPTS = 5

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def save(
        self,
        telegram_id: int,
        email: str,
        code: str,
    ) -> bool:
        """Сохранить код подтверждения для пользователя Telegram."""
        key = f"telegram:registration:{telegram_id}"
        value = json.dumps({"email": email, "code": code, "attempts": 0})

        saved = await self._redis.set(
            key,
            value,
            ex=self.CODE_TTL_SECONDS,
            nx=True,
        )

        return bool(saved)

    async def get(
        self,
        telegram_id: int,
    ) -> dict | None:
        """Получить код подтверждения для пользователя Telegram."""
        key = f"telegram:registration:{telegram_id}"
        value = await self._redis.get(key)
        if value is None:
            return None

        return json.loads(value)

    async def delete(
        self,
        telegram_id: int,
    ) -> None:
        """Удалить код подтверждения для пользователя Telegram."""
        key = f"telegram:registration:{telegram_id}"
        await self._redis.delete(key)

    async def verify(
        self,
        telegram_id: int,
        code: str,
    ) -> VerificationResult:
        """Проверить код подтверждения для пользователя Telegram."""
        key = f"telegram:registration:{telegram_id}"

        while True:
            async with self._redis.pipeline(transaction=True) as pipe:
                try:
                    await pipe.watch(key)
                    value = await pipe.get(key)

                    if value is None:
                        return VerificationResult(status=VerificationStatus.NO_ACTIVE_CODE)

                    data = json.loads(value)
                    if data["attempts"] >= self.MAX_ATTEMPTS:
                        return VerificationResult(status=VerificationStatus.BLOCKED)

                    is_valid = compare_digest(data["code"], code)
                    pipe.multi()

                    if is_valid:
                        pipe.delete(key) 
                    else:
                        data["attempts"] += 1
                        pipe.set(key, json.dumps(data), keepttl=True)

                    await pipe.execute()
                    if is_valid:
                        return VerificationResult(
                            status=VerificationStatus.VERIFIED,
                            email=data["email"],
                        )
                    else:
                        return VerificationResult(status=VerificationStatus.INVALID)

                except WatchError:
                    continue
