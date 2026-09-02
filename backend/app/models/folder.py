from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, String, Boolean, DateTime
from datetime import datetime
import uuid
from typing import List, Optional, TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.document import Document
    from app.models.user import User


class Folder(Base):
    __tablename__ = "doc_dg_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("doc_dg_folders.id", ondelete="CASCADE"), nullable=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam_dg_tenants.id"), index=True, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("iam_dg_users.id"), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trashed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="#1a73e8")

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    creator: Mapped[Optional["User"]] = relationship("User")
    
    parent: Mapped[Optional["Folder"]] = relationship("Folder", remote_side=[id], back_populates="subfolders")
    subfolders: Mapped[List["Folder"]] = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="folder")
