"""T59 — per-corpus calibration protocol, required before bulk-accept

Revision ID: 0019_corpus_calibration
Revises: 0018_records_amendment_chains
Create Date: 2026-08-24 00:00:11.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0019_corpus_calibration'
down_revision: Union[str, None] = '0018_records_amendment_chains'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sys_dg_corpus_calibration',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('corpus_folder_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calibrated_by_actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('calibrated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'corpus_folder_id', name='uq_corpus_calibration_tenant_folder'),
    )
    op.create_foreign_key('fk_corpus_calibration_tenant', 'sys_dg_corpus_calibration', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_corpus_calibration_folder', 'sys_dg_corpus_calibration', 'doc_dg_folders', ['corpus_folder_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_corpus_calibration_actor', 'sys_dg_corpus_calibration', 'iam_dg_users', ['calibrated_by_actor_id'], ['id'])
    op.create_index('idx_corpus_calibration_tenant_id', 'sys_dg_corpus_calibration', ['tenant_id'])
    op.create_index('idx_corpus_calibration_folder_id', 'sys_dg_corpus_calibration', ['corpus_folder_id'])

    op.execute("ALTER TABLE sys_dg_corpus_calibration ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sys_dg_corpus_calibration FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON sys_dg_corpus_calibration
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON sys_dg_corpus_calibration")
    op.execute("ALTER TABLE sys_dg_corpus_calibration NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sys_dg_corpus_calibration DISABLE ROW LEVEL SECURITY")
    op.drop_table('sys_dg_corpus_calibration')
