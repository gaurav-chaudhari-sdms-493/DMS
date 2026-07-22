from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Enum
from datetime import datetime
import uuid
import enum
from typing import List, Optional, TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.document_version import DocumentVersion
    from app.models.metadata_item import MetadataItem
    from app.models.chunk import Chunk

class DocStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("document_versions.id"), nullable=True)
    title: Mapped[str] = mapped_column()
    doc_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus, name="doc_status", create_type=False), default=DocStatus.pending)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="documents")
    versions: Mapped[List["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", foreign_keys="DocumentVersion.document_id")
    metadata_items: Mapped[List["MetadataItem"]] = relationship("MetadataItem", back_populates="document")
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", back_populates="document")
