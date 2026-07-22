from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, JSONB
from sqlalchemy import ForeignKey, TEXT, INTEGER, Computed
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional, Any

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document

class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    version_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("document_versions.id"), index=True, nullable=True)
    content: Mapped[str] = mapped_column(TEXT)
    content_tsv: Mapped[Optional[Any]] = mapped_column(TSVECTOR, Computed("to_tsvector('english', content)"), nullable=True)
    embedding: Mapped[Any] = mapped_column(Vector(1024))
    page_number: Mapped[Optional[int]] = mapped_column(INTEGER, nullable=True)
    chunk_index: Mapped[Optional[int]] = mapped_column(INTEGER, nullable=True)
    bbox: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
