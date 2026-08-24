from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Float
from datetime import datetime
import uuid
from typing import TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.fact import Fact


class FactRegion(Base):
    """The rectangle on a scanned page a fact came from (Section 0/2, decision T06).

    Origin (0,0) is the page's top-left corner; x grows right, y grows down.
    Coordinates are normalised 0-1 fractions of page width/height, not pixels,
    so a highlight stays correct at any zoom level. A fact can carry more than
    one region (Handler 3: continuation-row merge across two pages).
    """

    __tablename__ = "doc_dg_fact_regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    fact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_facts.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_pages.id", ondelete="CASCADE"), index=True)
    x0: Mapped[float] = mapped_column(Float, nullable=False)
    y0: Mapped[float] = mapped_column(Float, nullable=False)
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    fact: Mapped["Fact"] = relationship("Fact", back_populates="regions")
