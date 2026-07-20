from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from pgvector.sqlalchemy import Vector
from pgvector.sqlalchemy import TSVector
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
    content: Mapped[str] = mapped_column()
    page_number: Mapped[Optional[int]] = mapped_column()
    chunk_index: Mapped[int] = mapped_column()
    embedding: Mapped[Any] = mapped_column(Vector(1536))
    content_tsv: Mapped[Any] = mapped_column(TSVector())
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
