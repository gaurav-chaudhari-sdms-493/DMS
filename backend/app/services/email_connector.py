"""Email-in connector.

Polls a fixed IMAP mailbox for new messages and ingests each attachment
through the shared connector entry point (connector_ingest_service.ingest_bytes),
same pattern as the watched-folder and SFTP adapters.

Unlike a local file or an SFTP upload, an email arrives via SMTP as a single
atomic delivery — there's no "still being written" state to guard against,
so this connector skips the size/mtime stability check the other two need.

imaplib is a blocking library, so every IMAP call runs inside a thread
executor rather than directly on the event loop (same lesson as the SFTP
connector, and the BGE-M3 health-check bug earlier this session).

Demo scope: single fixed mailbox (see docker-compose 'mailserver' service —
a local test mail server, not real internet email), flat ingestion (no
subfolder mapping from email structure), messages marked \\Seen after
handling so they're never reprocessed.
"""
import asyncio
import hashlib
import imaplib
import logging
import mimetypes

from ..config import settings
from ..database import AsyncSessionLocal
from .connector_ingest_service import ingest_bytes, get_connector_actor, already_ingested
from .email_utils import extract_attachments

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 10


def _fetch_unseen_blocking() -> list[tuple[bytes, bytes]]:
    """One connection: fetch every unseen message's raw bytes, mark it \\Seen.
    Returns [(uid, raw_message_bytes), ...]."""
    imap = imaplib.IMAP4(settings.email_imap_host, settings.email_imap_port)
    try:
        imap.login(settings.email_username, settings.email_password)
        imap.select("INBOX")

        status, data = imap.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = data[0].split()
        results = []
        for msg_id in message_ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                logger.error("Email connector: failed to fetch message %s", msg_id)
                continue
            raw = msg_data[0][1]
            results.append((msg_id, raw))
            imap.store(msg_id, "+FLAGS", "\\Seen")  # never reprocess, success or fail

        return results
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()


def _extract_attachments(raw: bytes) -> list[tuple[str, bytes]]:
    """Parse a raw RFC822 message, return [(filename, content_bytes), ...] for
    every part that looks like a real file attachment (has a filename)."""
    return extract_attachments(raw)


async def poll_email_once() -> int:
    """Poll the mailbox once. Returns the count of attachments ingested."""
    if not settings.email_enabled:
        return 0

    loop = asyncio.get_running_loop()
    try:
        messages = await loop.run_in_executor(None, _fetch_unseen_blocking)
    except Exception as e:
        logger.error("Email connector: poll cycle failed to fetch: %s", e)
        return 0

    if not messages:
        return 0

    ingested = 0
    async with AsyncSessionLocal() as db:
        tenant_id, _ = await get_connector_actor(db)

        for msg_id, raw in messages:
            attachments = _extract_attachments(raw)
            if not attachments:
                logger.info("Email connector: message %s had no file attachments, skipping", msg_id)
                continue

            for filename, content in attachments:
                file_hash = hashlib.sha256(content).hexdigest()

                if await already_ingested(db, tenant_id, file_hash):
                    logger.info("Email connector: '%s' already ingested (hash match), skipping", filename)
                    continue

                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                try:
                    resp = await ingest_bytes(content, filename, db, content_type=content_type)
                    logger.info("Email connector: ingested '%s' from message %s as document %s", filename, msg_id, resp.document_id)
                    ingested += 1
                except Exception as e:
                    logger.error("Email connector: failed to ingest '%s' from message %s: %s", filename, msg_id, e)

    return ingested


async def email_poll_loop():
    if not settings.email_enabled:
        logger.info("Email connector disabled (EMAIL_ENABLED=false)")
        return

    logger.info(
        "Email connector started, watching %s (%s@%s:%s) every %ds",
        settings.email_address, settings.email_username, settings.email_imap_host,
        settings.email_imap_port, POLL_INTERVAL_SECONDS,
    )
    while True:
        try:
            await poll_email_once()
        except Exception as e:
            logger.error("Email poll cycle failed: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
