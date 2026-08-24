"""T04/T05 — page/fact/region schema, per the signed T06 coordinate contract

Stops discarding word-box coordinates: doc_dg_pages carries page-level
width/height/rotation/skew, doc_dg_facts carries one extracted value each,
and doc_dg_fact_regions carries the (possibly multiple, per Handler 3)
normalised 0-1 boxes a fact resolves to. A deferred constraint trigger
enforces at commit time that every fact has at least one region — "a fact
nobody can point at on the page is a fact nobody can check" (Section 2).

Revision ID: 0010_pages_facts_regions
Revises: 0009_sys_dg_config
Create Date: 2026-08-24 00:00:02.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0010_pages_facts_regions'
down_revision: Union[str, None] = '0009_sys_dg_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ['doc_dg_pages', 'doc_dg_facts', 'doc_dg_fact_regions']


def upgrade() -> None:
    op.create_table(
        'doc_dg_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('width', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('rotation', sa.Float(), nullable=False, server_default='0'),
        sa.Column('skew', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_doc_dg_pages_tenant', 'doc_dg_pages', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_doc_dg_pages_document', 'doc_dg_pages', 'doc_dg_documents', ['document_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_doc_dg_pages_version', 'doc_dg_pages', 'doc_dg_document_versions', ['version_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_doc_dg_pages_tenant_id', 'doc_dg_pages', ['tenant_id'])
    op.create_index('idx_doc_dg_pages_document_id', 'doc_dg_pages', ['document_id'])
    op.create_index('idx_doc_dg_pages_version_id', 'doc_dg_pages', ['version_id'])

    op.create_table(
        'doc_dg_facts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.Text(), nullable=False),
        sa.Column('value', postgresql.JSONB(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_doc_dg_facts_tenant', 'doc_dg_facts', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_doc_dg_facts_document', 'doc_dg_facts', 'doc_dg_documents', ['document_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_doc_dg_facts_version', 'doc_dg_facts', 'doc_dg_document_versions', ['version_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_doc_dg_facts_tenant_id', 'doc_dg_facts', ['tenant_id'])
    op.create_index('idx_doc_dg_facts_document_id', 'doc_dg_facts', ['document_id'])
    op.create_index('idx_doc_dg_facts_version_id', 'doc_dg_facts', ['version_id'])

    op.create_table(
        'doc_dg_fact_regions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('x0', sa.Float(), nullable=False),
        sa.Column('y0', sa.Float(), nullable=False),
        sa.Column('x1', sa.Float(), nullable=False),
        sa.Column('y1', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_doc_dg_fact_regions_tenant', 'doc_dg_fact_regions', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_doc_dg_fact_regions_fact', 'doc_dg_fact_regions', 'doc_dg_facts', ['fact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_doc_dg_fact_regions_page', 'doc_dg_fact_regions', 'doc_dg_pages', ['page_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_doc_dg_fact_regions_tenant_id', 'doc_dg_fact_regions', ['tenant_id'])
    op.create_index('idx_doc_dg_fact_regions_fact_id', 'doc_dg_fact_regions', ['fact_id'])
    op.create_index('idx_doc_dg_fact_regions_page_id', 'doc_dg_fact_regions', ['page_id'])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """)

    # Section 2 acceptance test: "Attempt to save a fact with an empty region
    # list -> the write must fail, not silently succeed." Deferred so a fact
    # and its region(s) can be inserted in the same transaction, in either order.
    op.execute("""
        CREATE OR REPLACE FUNCTION doc_dg_facts_require_region() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM doc_dg_fact_regions WHERE fact_id = NEW.id) THEN
                RAISE EXCEPTION 'fact % has no region — every fact must resolve to at least one region on a page (decision T06)', NEW.id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER doc_dg_facts_require_region_trigger
        AFTER INSERT OR UPDATE ON doc_dg_facts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION doc_dg_facts_require_region()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS doc_dg_facts_require_region_trigger ON doc_dg_facts")
    op.execute("DROP FUNCTION IF EXISTS doc_dg_facts_require_region()")

    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table('doc_dg_fact_regions')
    op.drop_table('doc_dg_facts')
    op.drop_table('doc_dg_pages')
