from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Boolean, Text
from datetime import datetime
from typing import Optional, Any
import uuid

from app.database import Base


class License(Base):
    """T81 — the currently-installed signed on-prem/air-gapped capacity
    license. Deployment-wide, not per-tenant: an on-prem install is one
    deployment, not a SaaS multi-tenant fleet. Stored so status can be
    shown without re-reading the license file off disk on every request;
    app/services/license_service.py re-verifies the signature at install
    time and caches the verdict in is_valid/invalid_reason.
    """

    __tablename__ = "billing_dg_license"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    signature_b64: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    invalid_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    installed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("iam_dg_users.id"), nullable=True)
    installed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
