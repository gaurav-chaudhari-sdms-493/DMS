from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Enum, UniqueConstraint
from datetime import datetime
import uuid
import enum
from typing import TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(index=True)
    full_name: Mapped[str] = mapped_column(default="")
    hashed_password: Mapped[str] = mapped_column("password_hash")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")