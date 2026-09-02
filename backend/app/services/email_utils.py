"""Email utilities for extracting attachments from raw RFC822 bytes.

Shared across legacy IMAP polling connector and the inbound webhook endpoint.
"""
import email
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def extract_attachments(raw: bytes) -> List[Tuple[str, bytes]]:
    """Parse a raw RFC822 message, return [(filename, content_bytes), ...] for
    every part that looks like a real file attachment (has a filename)."""
    msg = email.message_from_bytes(raw)
    attachments = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue  # inline body text, not a file
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        attachments.append((filename, payload))
    return attachments
