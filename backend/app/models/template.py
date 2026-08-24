from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import String, Text, UniqueConstraint
from datetime import datetime
from typing import Any
import uuid

from app.database import Base


class Template(Base):
    """A statutory form definition, keyed by form type x era (Section 12, T24).

    field_schema is a list of per-field dicts — name, type, required, and
    that field's own validation (pattern/min/max/allowed_values) — driven
    by data, not code, so a new form era never requires a deploy. Validation
    is written per template, never once for everything (Section 12).
    Global (not tenant-scoped): a form's layout doesn't vary per tenant.
    """

    __tablename__ = "doc_dg_templates"
    __table_args__ = (UniqueConstraint("form_type", "era_label", name="uq_doc_dg_templates_form_era"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    era_label: Mapped[str] = mapped_column(String, nullable=False)
    field_schema: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
