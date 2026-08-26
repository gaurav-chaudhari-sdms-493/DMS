from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Any

from app.database import Base


class OCRArchive(Base):
    """TS3 — archived raw OCR output, keyed by (file content hash, engine)
    so reprocessing the same file never re-runs OCR, and switching
    AI_OCR_PROVIDER never serves a different engine's cached result."""

    __tablename__ = "doc_dg_ocr_archive"

    content_hash: Mapped[str] = mapped_column(primary_key=True)
    ocr_engine: Mapped[str] = mapped_column(primary_key=True)
    pages: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
