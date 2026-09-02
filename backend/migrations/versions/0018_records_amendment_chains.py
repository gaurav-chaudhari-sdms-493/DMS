"""T60 — records module: base record + append-only amendment chain

Current state is never a stored mutable column — only derived by
replaying base_fields + amendments in effective_date order. This
migration creates the two tables only; the replay logic lives in
app/services/records_service.py, not the database.

Revision ID: 0018_records_amendment_chains
Revises: 0017_edge_batch_id_and_revert
Create Date: 2026-08-24 00:00:10.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0018_records_amendment_chains'
down_revision: Union[str, None] = '0017_edge_batch_id_and_revert'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ['record_dg_records', 'record_dg_amendments']


def upgrade() -> None:
    op.create_table(
        'record_dg_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_type', sa.Text(), nullable=False),
        sa.Column('base_fields', postgresql.JSONB(), nullable=False),
        sa.Column('base_evidence_fact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_policy_version', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_record_dg_records_tenant', 'record_dg_records', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_record_dg_records_subject_node', 'record_dg_records', 'entity_dg_nodes', ['subject_node_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_record_dg_records_base_evidence', 'record_dg_records', 'doc_dg_facts', ['base_evidence_fact_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_record_dg_records_actor', 'record_dg_records', 'iam_dg_users', ['created_by_actor_id'], ['id'])
    op.create_index('idx_record_dg_records_tenant_id', 'record_dg_records', ['tenant_id'])
    op.create_index('idx_record_dg_records_subject_node_id', 'record_dg_records', ['subject_node_id'])

    op.create_table(
        'record_dg_amendments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amendment_type', sa.Text(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('field_changes', postgresql.JSONB(), nullable=False),
        sa.Column('legal_status', sa.Text(), nullable=True),
        sa.Column('evidence_fact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_policy_version', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "legal_status IS NULL OR legal_status IN ('in force','set aside','under stay','superseded')",
            name="ck_record_dg_amendments_legal_status",
        ),
        sa.CheckConstraint(
            "created_by_actor_id IS NOT NULL OR created_by_policy_version IS NOT NULL",
            name="ck_record_dg_amendments_creator_present",
        ),
    )
    op.create_foreign_key('fk_record_dg_amendments_tenant', 'record_dg_amendments', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_record_dg_amendments_record', 'record_dg_amendments', 'record_dg_records', ['record_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_record_dg_amendments_evidence', 'record_dg_amendments', 'doc_dg_facts', ['evidence_fact_id'], ['id'])
    op.create_foreign_key('fk_record_dg_amendments_actor', 'record_dg_amendments', 'iam_dg_users', ['created_by_actor_id'], ['id'])
    op.create_index('idx_record_dg_amendments_tenant_id', 'record_dg_amendments', ['tenant_id'])
    op.create_index('idx_record_dg_amendments_record_id', 'record_dg_amendments', ['record_id'])
    op.create_index('idx_record_dg_amendments_effective_date', 'record_dg_amendments', ['effective_date'])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table('record_dg_amendments')
    op.drop_table('record_dg_records')
