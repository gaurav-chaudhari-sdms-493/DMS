from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
from typing import Optional
import uuid

from app.database import Base


class Subscription(Base):
    """T81 — which plan a tenant is on and its trial/period state. Plan
    limits themselves live in app/services/license_service.py:PLAN_DEFINITIONS,
    not here — this row only tracks the assignment.
    """

    __tablename__ = "billing_dg_subscription"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam_dg_tenants.id"), primary_key=True)
    plan_key: Mapped[str] = mapped_column(default="trial")
    status: Mapped[str] = mapped_column(default="trialing")  # trialing | active | expired | canceled
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
