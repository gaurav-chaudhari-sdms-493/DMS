"""T41 — doc_dg_document_versions.pdfa_s3_path.

Mandatory-on-ingest PDF/A-2b rendition, stored alongside (never replacing)
the original file — per the build design's "PDF/A-2b with original kept".
NULL when conversion wasn't attempted (non-PDF source) or failed (a failed
rendition must never block ingestion of the original).

Revision ID: 0043_pdfa_rendition
Revises: 0042_duplicate_candidates
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0043_pdfa_rendition'
down_revision: Union[str, None] = '0042_duplicate_candidates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_document_versions', sa.Column('pdfa_s3_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('doc_dg_document_versions', 'pdfa_s3_path')
