from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Text, Date, CheckConstraint
from datetime import date, datetime
from typing import Any, Optional
import uuid

from app.database import Base

VALID_LEGAL_STATUSES = ("in force", "set aside", "under stay", "superseded")


class RecordAmendment(Base):
    """One change to a Record — Section 7, T60. Append-only: amendments are
    never edited or deleted, only added. Current state is derived by
    replaying base_fields + every amendment in effective_date order —
    never stored as a mutable column that could drift out of sync with
    its own history.

    effective_date is the real-world date the change took legal effect
    (e.g. the ferfar's own date), not when it was entered into this
    system — a decades-old amendment discovered late still sorts into
    its correct place in the chain.
    """

    __tablename__ = "record_dg_amendments"
    __table_args__ = (
        CheckConstraint(
            "legal_status IS NULL OR legal_status IN ('in force','set aside','under stay','superseded')",
            name="ck_record_dg_amendments_legal_status",
        ),
        CheckConstraint(
            "created_by_actor_id IS NOT NULL OR created_by_policy_version IS NOT NULL",
            name="ck_record_dg_amendments_creator_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)

    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("record_dg_records.id", ondelete="CASCADE"), index=True)
    amendment_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "ferfar", "shuddhipatrak"
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    field_changes: Mapped[Any] = mapped_column(JSONB, nullable=False)
    legal_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # None = carries forward unchanged

    # Mandatory, unlike entity_dg_edges' evidence_fact_id — "each amendment
    # citing its source page" is a hard requirement here, not optional.
    evidence_fact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_facts.id"), nullable=False)

    created_by_actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_users.id"), nullable=True)
    created_by_policy_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
