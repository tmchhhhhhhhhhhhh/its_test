import logging
from email.message import EmailMessage

import aiosmtplib

from its_test.config import settings

logger = logging.getLogger("email")


async def send_verification_email(to_email: str, token: str) -> None:
    verify_link = f"{settings.base_url}/auth/verify-email?token={token}"

    if not settings.smtp_host:
        logger.info("[DEV MAIL] Подтверждение почты для %s: %s", to_email, verify_link)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = "Подтверждение регистрации"
    message.set_content(f"Для подтверждения почты перейдите по ссылке: {verify_link}")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
