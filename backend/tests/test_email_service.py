from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import send_password_reset_email


@pytest.mark.asyncio
async def test_send_password_reset_email_sends_via_smtp():
    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        await send_password_reset_email("someone@example.com", "reset-token-123")

        mock_smtp_cls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == "someone@example.com"
        assert "reset-token-123" in sent_msg.get_content()
        mock_server.quit.assert_called_once()


@pytest.mark.asyncio
async def test_send_password_reset_email_dev_mode_swallows_smtp_failure():
    from app.config import settings

    original_env = settings.app_env
    settings.app_env = "development"
    try:
        with patch("app.services.email_service.smtplib.SMTP", side_effect=OSError("connection refused")):
            # Should not raise — dev mode logs and moves on.
            await send_password_reset_email("someone@example.com", "reset-token-123")
    finally:
        settings.app_env = original_env


@pytest.mark.asyncio
async def test_send_password_reset_email_production_mode_raises_on_smtp_failure():
    from app.config import settings

    original_env = settings.app_env
    settings.app_env = "production"
    try:
        with patch("app.services.email_service.smtplib.SMTP", side_effect=OSError("connection refused")):
            with pytest.raises(OSError):
                await send_password_reset_email("someone@example.com", "reset-token-123")
    finally:
        settings.app_env = original_env
