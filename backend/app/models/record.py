from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Text
from datetime import datetime
from typing import Any, Optional
import uuid

from app.database import Base


class Record(Base):
    """The base entry of a record — Section 7, T60.

    "A land record is not a document. It is a first entry plus every
    change made to it since." base_fields is that first entry, exactly
    as written, and is never edited in place — every subsequent change
    is a RecordAmendment, replayed on top of this to derive current
    state. subject_node_id ties the record to the entity graph (T10):
    a record is always about some entity (typically a property).
    """

    __tablename__ = "record_dg_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)

    subject_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity_dg_nodes.id", ondelete="CASCADE"), index=True)
    record_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "7_12_extract", "form_a_entry"

    base_fields: Mapped[Any] = mapped_column(JSONB, nullable=False)
    base_evidence_fact_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("doc_dg_facts.id", ondelete="SET NULL"), nullable=True)

    created_by_actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_users.id"), nullable=True)
    created_by_policy_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # T66/D-7 — defaults to the never-purge class; a record is never engine-
    # purged by age regardless of what this is set to (see D7 decision doc).
    retention_class: Mapped[str] = mapped_column(
        ForeignKey("sys_dg_retention_classes.class_name"), nullable=False, default="statutory_record"
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
