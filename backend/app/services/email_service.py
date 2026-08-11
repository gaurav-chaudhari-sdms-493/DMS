import logging
from app.config import settings

logger = logging.getLogger(__name__)

async def send_password_reset_email(email: str, token: str) -> None:
    if settings.app_env == "production":
        raise NotImplementedError("SMTP not configured — refusing to send reset tokens in production")
    logger.debug("DEV ONLY — password reset token for %s: %s", email, token)
