from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Text
from datetime import datetime

from app.database import Base


class VLMArchive(Base):
    """TS3 — archived raw VLM response text, keyed by a hash of
    (file content hash, page number, exact prompt sent) so replaying a
    parsing/reconstruction fix (e.g. tuning table_stitch.py) never
    re-spends a Gemini call, and a template's field_schema changing
    naturally invalidates old cache entries (the prompt changes, so the
    key changes)."""

    __tablename__ = "doc_dg_vlm_archive"

    cache_key: Mapped[str] = mapped_column(primary_key=True)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
