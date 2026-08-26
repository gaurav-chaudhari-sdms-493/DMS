from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Float
from datetime import datetime
from typing import Optional
import uuid

from app.database import Base


class TableShapeDecision(Base):
    """TS1 — cached vertical/horizontal relation verdict for a pair of
    table-fragment shapes. See app/pipeline/table_stitch.py:shape_hash()."""

    __tablename__ = "doc_dg_table_shape_decisions"

    shape_hash: Mapped[str] = mapped_column(primary_key=True)
    relation: Mapped[str] = mapped_column()  # vertical | horizontal | unrelated
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decided_by: Mapped[str] = mapped_column()  # evidence | llm | human
    decided_by_actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("iam_dg_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
