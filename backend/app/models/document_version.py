from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document

class DocumentVersion(Base):
    __tablename__ = "doc_dg_document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_documents.id"), index=True)
    s3_path: Mapped[str] = mapped_column()
    # T41 — PDF/A-2b rendition, stored alongside the original (never
    # replacing it). NULL when not attempted (non-PDF) or failed.
    pdfa_s3_path: Mapped[Optional[str]] = mapped_column(nullable=True)
    version_number: Mapped[int] = mapped_column(default=1)
    file_hash: Mapped[str] = mapped_column()
    file_size_bytes: Mapped[int] = mapped_column()
    original_filename: Mapped[str] = mapped_column()
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_users.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="versions",
        foreign_keys="[DocumentVersion.document_id]"
    )
