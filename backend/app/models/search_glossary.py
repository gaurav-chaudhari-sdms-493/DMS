from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.database import Base


class SearchGlossaryTerm(Base):
    """TS7 — cross-script domain-vocabulary synonym groups. Every row
    sharing a canonical_key is a synonym of every other row in that
    group. See app/services/search_glossary_service.py."""

    __tablename__ = "sys_dg_search_glossary"

    term: Mapped[str] = mapped_column(String, primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String, index=True, nullable=False)
