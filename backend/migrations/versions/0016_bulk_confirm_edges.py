"""T57 — bulk threshold confirmation: record threshold/corpus/policy version
on every affected edge, not just the audit log

Revision ID: 0016_bulk_confirm_edges
Revises: 0015_entity_edge_confirmation
Create Date: 2026-08-24 00:00:08.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0016_bulk_confirm_edges'
down_revision: Union[str, None] = '0015_entity_edge_confirmation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('entity_dg_edges', sa.Column('verified_threshold', sa.Float(), nullable=True))
    op.add_column('entity_dg_edges', sa.Column('verified_corpus_folder_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('entity_dg_edges', sa.Column('verified_via_policy_version', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_entity_dg_edges_verified_corpus_folder',
        'entity_dg_edges', 'doc_dg_folders', ['verified_corpus_folder_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index('idx_entity_dg_edges_verified_corpus_folder_id', 'entity_dg_edges', ['verified_corpus_folder_id'])


def downgrade() -> None:
    op.drop_index('idx_entity_dg_edges_verified_corpus_folder_id', table_name='entity_dg_edges')
    op.drop_constraint('fk_entity_dg_edges_verified_corpus_folder', 'entity_dg_edges', type_='foreignkey')
    op.drop_column('entity_dg_edges', 'verified_via_policy_version')
    op.drop_column('entity_dg_edges', 'verified_corpus_folder_id')
    op.drop_column('entity_dg_edges', 'verified_threshold')
