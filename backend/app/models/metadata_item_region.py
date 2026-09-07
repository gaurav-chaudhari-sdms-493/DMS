from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Float, Integer
from datetime import datetime
import uuid
from typing import TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.metadata_item import MetadataItem


class MetadataItemRegion(Base):
    """T05 — the word-level box on a page a non-VLM (`doc_dg_metadata_items`)
    value came from. Same normalised 0-1, top-left-origin contract as
    FactRegion (T06), but keyed by a plain page_number rather than a
    doc_dg_pages FK: doc_dg_pages rows are only ever written by the VLM/T22
    path (see vlm_extraction.py's own comment on that), so most documents
    -- anything that never matched a classification template -- have none.
    Metadata extraction runs on every document regardless of classification,
    so this can't depend on doc_dg_pages existing.

    Unlike doc_dg_facts, a metadata item is allowed to have zero regions:
    the LLM-extracted value often doesn't appear verbatim in the page text
    (paraphrased, reformatted, or spanning a page break), and no region is
    a more honest result than a fabricated one -- no matching trigger here.
    """

    __tablename__ = "doc_dg_metadata_item_regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    metadata_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doc_dg_metadata_items.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x0: Mapped[float] = mapped_column(Float, nullable=False)
    y0: Mapped[float] = mapped_column(Float, nullable=False)
    x1: Mapped[float] = mapped_column(Float, nullable=False)
    y1: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    metadata_item: Mapped["MetadataItem"] = relationship("MetadataItem", back_populates="regions")
