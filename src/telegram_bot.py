import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiosmtplib import SMTPException
from redis.asyncio import Redis

from pydantic import ValidationError
from redis.exceptions import RedisError
import secrets
import logging

from task_notification.core.providers.setup import container
from task_notification.domain.use_cases.register_telegram_user import RegisterTelegramUserUseCase
from task_notification.infrastructure.telegram.registration_email import TelegramRegistrationEmailSender
from task_notification.infrastructure.telegram.registration_store import TelegramRegistrationStore, VerificationStatus
from task_notification.schemas.user_telegram import UserTelegramCreate
from task_notification.core.config import settings


dispatcher = Dispatcher()

logger = logging.getLogger(__name__)


class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_code = State()


@dispatcher.message(Command("start"))
async def start_command(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await message.answer("Привет! Я бот уведомлений о задачах.\n\nДля регистрации используйте /register")


@dispatcher.message(Command("register"))
async def register_command(
    message: Message,
    state: FSMContext,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Регистрация доступна только в личном чате с ботом.")
        return

    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer("Пожалуйста, введите ваш email для регистрации.")


@dispatcher.message(Command("confirm"))
async def confirm_command(
    message: Message,
    state: FSMContext,
) -> None:
    if message.chat.type != ChatType.PRIVATE:
        await message.answer("Подтверждение доступно только в личном чате с ботом.")
        return
    
    await state.set_state(RegistrationStates.waiting_for_code)
    await message.answer("Введите код подтверждения:")


@dispatcher.message(RegistrationStates.waiting_for_email)
async def process_email(
    message: Message,
    state: FSMContext,
    registration_store: TelegramRegistrationStore,
    registration_email_sender: TelegramRegistrationEmailSender,
) -> None:

    if message.from_user is None:
        await state.clear()
        await message.answer("Не удалось определить пользователя.")
        return

    email = (message.text or "").strip()

    try:
        registration = UserTelegramCreate(
            email=email,
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
        )

    except ValidationError:
        await message.answer("Проверьть email адрес и попробуйте ещё раз.")
        return

    code = f"{secrets.randbelow(10_000):04d}"

    try:
        saved = await registration_store.save(
            telegram_id=registration.telegram_id,
            email=str(registration.email),
            code=code,
        )

    except RedisError:
        logger.exception("Не удалось сохранить код регистрации в Redis")
        await state.clear()
        await message.answer("Произошла ошибка при обработке регистрации. Попробуйте ещё раз позже.")
        return

    if not saved:
        await state.clear()
        await message.answer("Код уже был отправлен. Используйте команду /confirm.")
        return

    try:
        await registration_email_sender.send_code(
            email=str(registration.email),
            code=code,
        )

    except (SMTPException, OSError):
        logger.exception("Не удалось отправить код подтверждения на email")

        try:
            await registration_store.delete(registration.telegram_id)

        except RedisError:
            logger.exception("Не удалось удалить неотправленный код")

        await state.clear()
        await message.answer("Не удалось отправить письмо. Попробуйте позже.")
        return
    
    await state.clear()
    await message.answer(f"Код отправлен на email и действует 10 минут.\nДля его ввода используйте /confirm.")


@dispatcher.message(RegistrationStates.waiting_for_code)
async def process_confirmation_code(
    message: Message,
    state: FSMContext,
    registration_store: TelegramRegistrationStore,
) -> None:
    
    if message.from_user is None:
        await state.clear()
        await message.answer("Не удалось определить пользователя.")
        return

    code = (message.text or "").strip()

    if len(code) != 4 or not code.isascii() or not code.isdigit():
        await message.answer("Код должен состоять из 4 цифр. Попробуйте ещё раз.")
        return

    try:
        result = await registration_store.verify(
            telegram_id=message.from_user.id,
            code=code,
        )

    except RedisError:
        logger.exception("Не удалось проверить код регистрации в Redis")
        await state.clear()
        await message.answer("Произошла ошибка при обработке кода. Попробуйте ещё раз позже.")
        return

    if result.status == VerificationStatus.NO_ACTIVE_CODE:
        await state.clear()
        await message.answer("Нет активного кода подтверждения. Пожалуйста, используйте /register для получения нового кода.")
        return

    if result.status == VerificationStatus.BLOCKED:
        await state.clear()
        await message.answer("Количество попыток исчерпано. После окончания 10 минут запросите новый код.")
        return

    if result.status == VerificationStatus.INVALID:
        await message.answer("Неверный код. Попробуйте ещё раз:")
        return

    if result.email is None:
        logger.error("У подтверждённой регистрации отсутствует email")
        await state.clear()
        await message.answer("Не удалось завершить регистрацию. Попробуйте ещё раз позже.")
        return

    try:
        async with container() as request_conteiner:
            use_case = await request_conteiner.get(RegisterTelegramUserUseCase)

            await use_case.execute(
                UserTelegramCreate(
                    email=result.email,
                    telegram_id=message.from_user.id,
                    telegram_username=message.from_user.username,
                )
            )

    except Exception:
        logger.exception("Не удалось сохранить Telegram-привязку")
        await state.clear()
        await message.answer("Не удалось завершить регистрацию. Попробуйте ещё раз позже.")
        return

    await state.clear()
    await message.answer("Регистрация успешно завершена! Теперь вы будете получать уведомления о задачах.")
    

async def main() -> None:
    if not settings.TELEGRAM_BOT_ENABLED:
        raise RuntimeError("Telegram-бот отключён")

    if settings.TELEGRAM_BOT_TOKEN is None:
        raise RuntimeError("Не указан токен Telegram-бота")

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN.get_secret_value())

    async with Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    ) as redis:
        await redis.ping()
        await dispatcher.start_polling(
            bot,
            registration_store=TelegramRegistrationStore(redis),
            registration_email_sender=TelegramRegistrationEmailSender(),
        )


if __name__ == "__main__":
    asyncio.run(main())