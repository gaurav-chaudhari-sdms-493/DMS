from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid

from app.database import Base

class Permission(Base):
    __tablename__ = "iam_dg_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_users.id"), index=True)
    resource_type: Mapped[str] = mapped_column()
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
