"""T58 — verified_batch_id, a precise handle for undoing one bulk-confirm run

Revision ID: 0017_edge_batch_id_and_revert
Revises: 0016_bulk_confirm_edges
Create Date: 2026-08-24 00:00:09.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0017_edge_batch_id_and_revert'
down_revision: Union[str, None] = '0016_bulk_confirm_edges'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('entity_dg_edges', sa.Column('verified_batch_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('idx_entity_dg_edges_verified_batch_id', 'entity_dg_edges', ['verified_batch_id'])


def downgrade() -> None:
    op.drop_index('idx_entity_dg_edges_verified_batch_id', table_name='entity_dg_edges')
    op.drop_column('entity_dg_edges', 'verified_batch_id')
