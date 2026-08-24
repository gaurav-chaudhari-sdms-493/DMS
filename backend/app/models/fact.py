from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Float, Text
from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from app.database import Base

if TYPE_CHECKING:
    from app.models.fact_region import FactRegion


class Fact(Base):
    """One value pulled out of a document — a name, an area, a date (Section 0).

    Every fact must resolve to at least one region on a page. That's enforced
    at commit time by the doc_dg_facts_require_region trigger (migration
    0010), not just hidden in the UI — a fact nobody can point at on the page
    is a fact nobody can check.
    """

    __tablename__ = "doc_dg_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_documents.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_document_versions.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    regions: Mapped[List["FactRegion"]] = relationship(
        "FactRegion", back_populates="fact", cascade="all, delete-orphan"
    )
