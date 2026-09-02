from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, Integer
from datetime import datetime
from typing import Optional

from app.database import Base


class RetentionClass(Base):
    """T66/D-7 — a named retention policy, global like doc_dg_templates
    (a class definition doesn't vary per tenant). retention_days is NULL
    for a permanent (never engine-purged) class — the D-7 default for
    anything not explicitly classified.
    """

    __tablename__ = "sys_dg_retention_classes"

    class_name: Mapped[str] = mapped_column(Text, primary_key=True)
    retention_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
