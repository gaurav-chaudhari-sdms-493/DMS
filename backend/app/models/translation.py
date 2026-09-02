from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text, PrimaryKeyConstraint

from app.database import Base


class Translation(Base):
    """T95 — sys_dg_translations. (locale, key) -> value, served to the
    frontend via GET /api/v1/i18n/{locale} rather than bundled as static
    JSON, so a translation can be corrected without a redeploy."""

    __tablename__ = "sys_dg_translations"
    __table_args__ = (PrimaryKeyConstraint("locale", "key", name="pk_sys_dg_translations"),)

    locale: Mapped[str] = mapped_column()
    key: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column(Text())
