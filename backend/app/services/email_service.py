import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def _send_smtp_sync(msg: EmailMessage) -> None:
    if settings.smtp_use_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    try:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    finally:
        server.quit()


async def send_password_reset_email(email: str, token: str) -> None:
    if not settings.smtp_username or settings.smtp_host == "mailserver":
        logger.warning(
            "SMTP is pointed at the local GreenMail test server, not a real "
            "mail provider — reset emails will NOT reach real inboxes until "
            "real SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD are set in .env"
        )

    msg = EmailMessage()
    msg["Subject"] = "VeritasDocs — Password Reset Code"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = email
    msg.set_content(
        "We received a request to reset your VeritasDocs password.\n\n"
        f"Your reset code is: {token}\n\n"
        "Enter this code on the password reset page to choose a new password. "
        "If you didn't request this, you can safely ignore this email."
    )

    try:
        await asyncio.to_thread(_send_smtp_sync, msg)
        logger.info("Password reset email sent to %s", email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", email)
        if settings.app_env == "production":
            raise


async def send_ingestion_failure_alert(email: str, document_title: str, reason: str) -> None:
    """T41 — mandatory-on-ingest failure alerting. Previously logger-only
    (a failed document silently sat as status='failed' until someone
    happened to look); this actually notifies the person who can act on
    it — the uploader, since they're the one who knows whether the file
    was ever readable and can decide to re-upload or investigate.
    Best-effort: never raises, an alert that can't be sent must never
    fail the ingestion-failure recording it's reporting on.
    """
    msg = EmailMessage()
    msg["Subject"] = f"Document processing failed: {document_title}"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = email
    msg.set_content(
        f'Your document "{document_title}" could not be processed.\n\n'
        f"Reason: {reason}\n\n"
        "The original file has been kept and can be re-uploaded (safe to retry — "
        "an unchanged file is detected and never reprocessed twice). If this "
        "keeps happening, contact your administrator."
    )
    try:
        await asyncio.to_thread(_send_smtp_sync, msg)
        logger.info("Ingestion failure alert sent to %s for document %r", email, document_title)
    except Exception:
        logger.exception("Failed to send ingestion failure alert to %s", email)
