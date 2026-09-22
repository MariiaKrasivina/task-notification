from email.message import EmailMessage

from aiosmtplib import SMTP

from task_notification.core.config import settings


class TelegramRegistrationEmailSender:
    async def send_code(self, email: str, code: str) -> None:
        """Отправить код подтверждения на email."""

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = email
        message["Subject"] = "Подтверждение регистрации в Telegram-боте"
        message.set_content(
            f"Ваш код подтверждения для регистрации в Telegram-боте: {code}\n"
            "Код действителен 10 минут.\n\n"
            "Если вы не пытались зарегистрироваться, просто проигнорируйте это письмо."
        )

        smtp = SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            start_tls=settings.SMTP_START_TLS,
        )

        async with smtp:
            await smtp.send_message(message)