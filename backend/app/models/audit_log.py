from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from typing import Optional, Any

from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_dg_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_tenants.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column()
    resource_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True)
    details: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # T63 — tamper-evident hash chain, anchored per tenant. NULL on rows
    # written before this migration: "adding a chain later proves nothing
    # about rows written before it" (Section 12) — those rows are honestly
    # left unprotected rather than backfilled with a fabricated hash.
    previous_hash: Mapped[Optional[str]] = mapped_column(nullable=True)
    event_hash: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
