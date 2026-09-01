from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Float, Text
from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document


class MetadataItem(Base):
    """Structured metadata extracted from a document, stored as key-value pairs.

    Each row represents a single extracted field (e.g. key='author', value={'v': 'Jane Smith'}).
    The value column is JSONB to support both scalar and structured values.
    """

    __tablename__ = "doc_dg_metadata_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("iam_dg_tenants.id"), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doc_dg_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="llm")
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="metadata_items")
