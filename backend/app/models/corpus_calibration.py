from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Text, Integer, UniqueConstraint
from datetime import datetime
from typing import Optional
import uuid

from app.database import Base


class CorpusCalibration(Base):
    """T59 — a corpus must be explicitly certified calibrated before bulk
    threshold confirmation (T57) is allowed to run against it.

    A hardcoded confidence like the old 0.9 "implies calibrated confidence
    and carries none — any threshold built on it is meaningless"
    (scope gap, engineering standards). This doesn't solve the calibration
    methodology itself (that's D-5, still undecided) — it's the governance
    checkpoint: a named human attests they validated this corpus's
    confidence scores before anyone is allowed to bulk-accept off them.
    Always requires a real actor; a policy/rule can never self-certify.
    """

    __tablename__ = "sys_dg_corpus_calibration"
    __table_args__ = (
        UniqueConstraint("tenant_id", "corpus_folder_id", name="uq_corpus_calibration_tenant_folder"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)

    corpus_folder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doc_dg_folders.id", ondelete="CASCADE"), index=True)
    calibrated_by_actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_users.id"), nullable=False)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    calibrated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
