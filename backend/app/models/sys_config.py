from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String, Text
from datetime import datetime
from typing import Any

from app.database import Base


class SysConfig(Base):
    """Every threshold and limit the app uses, in one place, with a documented default.

    value is JSONB wrapping the actual typed value as {"v": ...}, matching the
    same convention MetadataItem already uses for its own value column.
    """

    __tablename__ = "sys_dg_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
