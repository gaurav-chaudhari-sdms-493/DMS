from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Boolean, DateTime
from datetime import datetime
import uuid
from typing import List, Optional, TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.document_version import DocumentVersion
    from app.models.metadata_item import MetadataItem
    from app.models.chunk import Chunk
    from app.models.folder import Folder

class Document(Base):
    __tablename__ = "doc_dg_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_users.id"), index=True, nullable=True)
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("doc_dg_document_versions.id", use_alter=True, name="fk_doc_dg_documents_current_version"), nullable=True)
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("doc_dg_folders.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column()
    doc_type: Mapped[Optional[str]] = mapped_column()
    mime_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trashed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # T66/D-7 — governs whether/when the retention engine may purge this
    # document once trashed. Defaults to the never-purge class; only
    # 'operational_trash' has a finite period (see D7 decision doc).
    retention_class: Mapped[str] = mapped_column(
        ForeignKey("sys_dg_retention_classes.class_name"), default="unclassified_permanent", nullable=False
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="documents")
    folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="documents")
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        foreign_keys="[DocumentVersion.document_id]"
    )
    metadata_items: Mapped[List["MetadataItem"]] = relationship("MetadataItem", back_populates="document")
    chunks: Mapped[List["Chunk"]] = relationship("Chunk", back_populates="document")

