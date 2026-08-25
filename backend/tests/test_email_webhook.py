import base64
import email.mime.application
import email.mime.multipart
import email.mime.text
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.services.email_utils import extract_attachments


def build_raw_email_with_attachments(attachments=None) -> bytes:
    """Helper to build a raw MIME RFC822 email bytes payload."""
    msg = email.mime.multipart.MIMEMultipart()
    msg["From"] = "sender@example.com"
    msg["To"] = "uploads@ourdomain.com"
    msg["Subject"] = "Document Ingestion Test"

    # Add text body part
    body = email.mime.text.MIMEText("Hello, please find the documents attached.", "plain")
    msg.attach(body)

    if attachments:
        for filename, content in attachments:
            part = email.mime.application.MIMEApplication(content, Name=filename)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)

    return msg.as_bytes()


def test_extract_attachments_no_attachments():
    raw = build_raw_email_with_attachments(attachments=[])
    result = extract_attachments(raw)
    assert result == []


def test_extract_attachments_with_files():
    attachments_input = [
        ("report.pdf", b"%PDF-1.4 test content"),
        ("data.csv", b"col1,col2\nval1,val2"),
    ]
    raw = build_raw_email_with_attachments(attachments=attachments_input)
    extracted = extract_attachments(raw)

    assert len(extracted) == 2
    assert extracted[0] == ("report.pdf", b"%PDF-1.4 test content")
    assert extracted[1] == ("data.csv", b"col1,col2\nval1,val2")


@pytest.mark.asyncio
async def test_email_webhook_unauthorized_missing_secret():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/connectors/email-inbound",
            json={"raw_email_b64": "dGVzdA=="},
        )
    assert res.status_code == 401
    assert "Invalid or missing webhook secret header" in res.json()["detail"]


@pytest.mark.asyncio
async def test_email_webhook_unauthorized_wrong_secret():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/connectors/email-inbound",
            headers={"X-Webhook-Secret": "wrong_secret"},
            json={"raw_email_b64": "dGVzdA=="},
        )
    assert res.status_code == 401
    assert "Invalid or missing webhook secret header" in res.json()["detail"]


@pytest.mark.asyncio
async def test_email_webhook_bad_base64():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/connectors/email-inbound",
            headers={"X-Webhook-Secret": settings.email_webhook_secret},
            json={"raw_email_b64": "!!!not_base64!!!"},
        )
    assert res.status_code == 400
    assert "Invalid base64 payload" in res.json()["detail"]


@pytest.mark.asyncio
async def test_email_webhook_ingest_flow():
    raw_email = build_raw_email_with_attachments([
        ("invoice.pdf", b"%PDF-1.4 invoice content"),
        ("duplicate.pdf", b"%PDF-1.4 existing content"),
    ])
    b64_email = base64.b64encode(raw_email).decode("utf-8")

    mock_resp = AsyncMock()
    mock_resp.document_id = "11111111-2222-3333-4444-555555555555"

    with patch("app.api.v1.email_webhook.get_connector_actor") as mock_actor, \
         patch("app.api.v1.email_webhook.already_ingested") as mock_dedup, \
         patch("app.api.v1.email_webhook.ingest_bytes", return_value=mock_resp) as mock_ingest:

        mock_actor.return_value = ("tenant-uuid", "user-uuid")
        # First file new (False), second file duplicate (True)
        mock_dedup.side_effect = [False, True]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/connectors/email-inbound",
                headers={"X-Webhook-Secret": settings.email_webhook_secret},
                json={"raw_email_b64": b64_email},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["attachments_processed"] == 2
        assert body["attachments_ingested"] == 1
        assert body["attachments_skipped_duplicate"] == 1
        assert len(body["ingested_details"]) == 1
        assert body["ingested_details"][0]["filename"] == "invoice.pdf"
        assert body["ingested_details"][0]["document_id"] == "11111111-2222-3333-4444-555555555555"
