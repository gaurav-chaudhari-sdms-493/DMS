from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Float, Integer
from datetime import datetime
import uuid

from app.database import Base


class DocumentPage(Base):
    """One row per scanned page — width/height/rotation/skew, per decision T06.

    Rotation and skew live here, not on the region: T06 says a region reads
    its parent page's rotation rather than storing its own.
    """

    __tablename__ = "doc_dg_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_documents.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_document_versions.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    rotation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skew: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
