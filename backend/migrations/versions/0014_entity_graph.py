"""T10 — property-graph schema: entity_dg_nodes and entity_dg_edges

Decisions D-1 (nested folders, accepted change) and T09 (architecture
doc — plain Postgres tables, not Apache AGE, for the entity graph) are
both signed; this is the schema itself. Business logic for tiered
auto-commit / escrow / bulk-threshold confirmation (T56-T59) is
explicitly NOT part of this migration — schema only, per the T10
backlog scope.

Revision ID: 0014_entity_graph
Revises: 0013_devanagari_tsvector
Create Date: 2026-08-24 00:00:06.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0014_entity_graph'
down_revision: Union[str, None] = '0013_devanagari_tsvector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ['entity_dg_nodes', 'entity_dg_edges']


def upgrade() -> None:
    op.create_table(
        'entity_dg_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('attributes', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_entity_dg_nodes_tenant', 'entity_dg_nodes', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_index('idx_entity_dg_nodes_tenant_id', 'entity_dg_nodes', ['tenant_id'])
    op.create_index('idx_entity_dg_nodes_entity_type', 'entity_dg_nodes', ['entity_type'])

    op.create_table(
        'entity_dg_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edge_type', sa.Text(), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.Text(), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_fact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='machine'),
        sa.Column('created_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_policy_version', sa.Text(), nullable=True),
        sa.Column('evidence_fact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tier IN (1,2,3,4)", name="ck_entity_dg_edges_tier"),
        sa.CheckConstraint("status IN ('machine','held','verified')", name="ck_entity_dg_edges_status"),
        sa.CheckConstraint("target_type IN ('entity','fact')", name="ck_entity_dg_edges_target_type"),
        sa.CheckConstraint(
            "created_by_actor_id IS NOT NULL OR created_by_policy_version IS NOT NULL",
            name="ck_entity_dg_edges_creator_present",
        ),
    )
    op.create_foreign_key('fk_entity_dg_edges_tenant', 'entity_dg_edges', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_entity_dg_edges_source_node', 'entity_dg_edges', 'entity_dg_nodes', ['source_node_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_entity_dg_edges_target_node', 'entity_dg_edges', 'entity_dg_nodes', ['target_node_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_entity_dg_edges_target_fact', 'entity_dg_edges', 'doc_dg_facts', ['target_fact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_entity_dg_edges_evidence_fact', 'entity_dg_edges', 'doc_dg_facts', ['evidence_fact_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_entity_dg_edges_actor', 'entity_dg_edges', 'iam_dg_users', ['created_by_actor_id'], ['id'])
    op.create_index('idx_entity_dg_edges_tenant_id', 'entity_dg_edges', ['tenant_id'])
    op.create_index('idx_entity_dg_edges_source_node_id', 'entity_dg_edges', ['source_node_id'])
    op.create_index('idx_entity_dg_edges_target_node_id', 'entity_dg_edges', ['target_node_id'])
    op.create_index('idx_entity_dg_edges_target_fact_id', 'entity_dg_edges', ['target_fact_id'])
    op.create_index('idx_entity_dg_edges_tier', 'entity_dg_edges', ['tier'])
    op.create_index('idx_entity_dg_edges_status', 'entity_dg_edges', ['status'])

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

    op.drop_table('entity_dg_edges')
    op.drop_table('entity_dg_nodes')
