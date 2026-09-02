"""TS2 — data-loss audit columns on doc_dg_documents.

data_loss_words_missing is always populated at ingest (0 = clean, same
convention as T76's pages_failed_count); data_loss_details only holds a
capped sample of the actual missing words + their page numbers, and only
when missing_count > 0, so a clean document's row stays lean.

Revision ID: 0035_data_loss_audit
Revises: 0034_table_shape_decisions
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '0035_data_loss_audit'
down_revision: Union[str, None] = '0034_table_shape_decisions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_documents', sa.Column('data_loss_words_missing', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('doc_dg_documents', sa.Column('data_loss_details', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('doc_dg_documents', 'data_loss_details')
    op.drop_column('doc_dg_documents', 'data_loss_words_missing')
