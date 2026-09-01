"""TS3 — OCR/VLM raw-response archival, content-hash keyed.

Both tables are content-addressed and deliberately NOT tenant-scoped:
the OCR/VLM output for a given (file bytes, prompt) is a pure function
of that input, never of who asked — two tenants uploading byte-identical
files get the byte-identical cached result, same as a CDN cache. Actual
tenant data (Documents, Chunks, Facts) stays exactly as tenant-isolated
as before; only this intermediate, re-derivable artifact is shared.

Revision ID: 0036_extraction_archive
Revises: 0035_data_loss_audit
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '0036_extraction_archive'
down_revision: Union[str, None] = '0035_data_loss_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doc_dg_ocr_archive',
        sa.Column('content_hash', sa.String(length=64), primary_key=True),
        sa.Column('ocr_engine', sa.String(), primary_key=True),
        sa.Column('pages', JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        'doc_dg_vlm_archive',
        sa.Column('cache_key', sa.String(length=64), primary_key=True),
        sa.Column('raw_response', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('doc_dg_vlm_archive')
    op.drop_table('doc_dg_ocr_archive')
