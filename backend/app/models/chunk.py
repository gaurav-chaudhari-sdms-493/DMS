from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, TEXT, INTEGER, Index
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Optional, Any

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document

class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_versions.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    content: Mapped[str] = mapped_column(TEXT)
    embedding: Mapped[Any] = mapped_column(Vector(1536))
    chunk_metadata: Mapped[dict] = mapped_column(JSONB)
    page_number: Mapped[Optional[int]] = mapped_column(INTEGER)
    chunk_index: Mapped[int] = mapped_column(INTEGER)
    s3_path: Mapped[str] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
