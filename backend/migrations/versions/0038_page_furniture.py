"""TS6 — page-furniture detection: doc_dg_documents.page_furniture_candidates.

Detection only, never applied to chunk content — nothing this migration
enables changes what's stored/searched, it's a new informational signal
computed at ingest. NULL for the common case (nothing detected), same
convention as TS2's data_loss_details.

Revision ID: 0038_page_furniture
Revises: 0037_field_trust_signal
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '0038_page_furniture'
down_revision: Union[str, None] = '0037_field_trust_signal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_documents', sa.Column('page_furniture_candidates', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('doc_dg_documents', 'page_furniture_candidates')
