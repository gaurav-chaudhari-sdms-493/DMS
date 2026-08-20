"""Shared ingestion entry point for non-HTTP connector sources.

Watched folder, FTP/SFTP, and email-in adapters all call `ingest_bytes()`
below instead of duplicating upload logic. It wraps raw bytes into the
same `UploadFile` path the manual HTTP upload uses, so hashing, storage,
and the Celery hand-off behave identically no matter which source the
file came from.

Demo scope: connectors run as a single fixed actor (DEFAULT_CONNECTOR_EMAIL)
rather than resolving per-source tenant/user mapping. That mapping is real
production scope (see backlog T40), not a one-night addition.
"""
import io
import logging
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.document import Document
from ..models.document_version import DocumentVersion
from ..models.user import User
from .document_service import upload_document
from ..schemas.document import DocumentUploadResponse

logger = logging.getLogger(__name__)

DEFAULT_CONNECTOR_EMAIL = "admin@example.com"

_actor_cache: dict[str, tuple[UUID, UUID]] = {}


async def get_connector_actor(db: AsyncSession, email: str = DEFAULT_CONNECTOR_EMAIL) -> tuple[UUID, UUID]:
    """Resolve (tenant_id, user_id) for the fixed connector identity, cached per email."""
    if email in _actor_cache:
        return _actor_cache[email]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise RuntimeError(
            f"Connector actor '{email}' not found. Sign up this user first, "
            "or point DEFAULT_CONNECTOR_EMAIL at an existing account."
        )

    identity = (user.tenant_id, user.id)
    _actor_cache[email] = identity
    return identity


async def already_ingested(db: AsyncSession, tenant_id: UUID, file_hash: str) -> bool:
    """Shared hash-based dedup check, used by every connector before ingesting a file."""
    result = await db.execute(
        select(DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(DocumentVersion.file_hash == file_hash, Document.tenant_id == tenant_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def ingest_bytes(
    content: bytes,
    filename: str,
    db: AsyncSession,
    content_type: str = "application/octet-stream",
    folder_id: Optional[UUID] = None,
    actor_email: str = DEFAULT_CONNECTOR_EMAIL,
) -> DocumentUploadResponse:
    """Ingest raw bytes from a connector source through the standard upload path."""
    tenant_id, user_id = await get_connector_actor(db, actor_email)

    upload_file = UploadFile(
        file=io.BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )

    logger.info("Connector ingest: %s (%d bytes) as tenant=%s user=%s", filename, len(content), tenant_id, user_id)
    return await upload_document(upload_file, tenant_id, user_id, db, folder_id=folder_id)
