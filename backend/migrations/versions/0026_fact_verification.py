"""T51/T52/T54 — fact verification: the workbench's state-machine columns

Mirrors entity_dg_edges' verification-audit columns (T56/T57) exactly, so
the fact lane and the entity-edge lane of the two-lane model work the same
way. is_handwritten is new — T55's hard rule ("no handwritten-source
verified data without confirmation") needs something to check; it
defaults False and nothing sets it True yet (T30, the handwritten/
degraded capture policy, isn't built) — it exists now so bulk_confirm can
already refuse to auto-promote a handwritten fact once something does set
it, rather than needing another migration later.

Revision ID: 0026_fact_verification
Revises: 0025_document_classification
Create Date: 2026-08-24 00:00:14.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0026_fact_verification'
down_revision: Union[str, None] = '0025_document_classification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_facts', sa.Column('is_handwritten', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('doc_dg_facts', sa.Column('claimed_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('claimed_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_doc_dg_facts_claimed_by', 'doc_dg_facts', 'iam_dg_users', ['claimed_by_actor_id'], ['id'])

    op.add_column('doc_dg_facts', sa.Column('verified_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('verified_threshold', sa.Float(), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('verified_corpus_folder_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('verified_via_policy_version', sa.Text(), nullable=True))
    op.add_column('doc_dg_facts', sa.Column('verified_batch_id', postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key('fk_doc_dg_facts_verified_by', 'doc_dg_facts', 'iam_dg_users', ['verified_by_actor_id'], ['id'])
    op.create_foreign_key('fk_doc_dg_facts_verified_corpus_folder', 'doc_dg_facts', 'doc_dg_folders', ['verified_corpus_folder_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_doc_dg_facts_verified_batch_id', 'doc_dg_facts', ['verified_batch_id'])


def downgrade() -> None:
    op.drop_index('idx_doc_dg_facts_verified_batch_id', table_name='doc_dg_facts')
    op.drop_constraint('fk_doc_dg_facts_verified_corpus_folder', 'doc_dg_facts', type_='foreignkey')
    op.drop_constraint('fk_doc_dg_facts_verified_by', 'doc_dg_facts', type_='foreignkey')
    for col in ['verified_batch_id', 'verified_via_policy_version', 'verified_corpus_folder_id',
                'verified_threshold', 'verified_at', 'verified_by_actor_id']:
        op.drop_column('doc_dg_facts', col)
    op.drop_constraint('fk_doc_dg_facts_claimed_by', 'doc_dg_facts', type_='foreignkey')
    op.drop_column('doc_dg_facts', 'claimed_at')
    op.drop_column('doc_dg_facts', 'claimed_by_actor_id')
    op.drop_column('doc_dg_facts', 'is_handwritten')
