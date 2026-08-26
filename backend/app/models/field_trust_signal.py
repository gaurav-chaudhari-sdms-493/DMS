from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class FieldTrustSignal(Base):
    """TS4 — how often a given field_name's low-confidence readings have
    historically been confirmed correct vs corrected as wrong. See
    app/services/field_trust_service.py."""

    __tablename__ = "doc_dg_field_trust_signal"

    field_name: Mapped[str] = mapped_column(primary_key=True)
    confirmed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    corrected_count: Mapped[int] = mapped_column(default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
