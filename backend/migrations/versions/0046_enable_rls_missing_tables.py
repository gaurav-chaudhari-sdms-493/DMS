"""enable row level security on metadata_items, document_versions, templates, and retention_classes

Revision ID: 0040_enable_rls_missing_tables
Revises: 0039_search_glossary
Create Date: 2026-08-31 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0046_enable_rls_missing_tables'
down_revision: Union[str, None] = '0045_seed_starter_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. doc_dg_metadata_items
    op.add_column('doc_dg_metadata_items', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE doc_dg_metadata_items m
        SET tenant_id = d.tenant_id
        FROM doc_dg_documents d
        WHERE m.document_id = d.id
    """)
    op.alter_column('doc_dg_metadata_items', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_doc_dg_metadata_items_tenant', 'doc_dg_metadata_items', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_index('idx_doc_dg_metadata_items_tenant_id', 'doc_dg_metadata_items', ['tenant_id'])

    op.execute("ALTER TABLE doc_dg_metadata_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_metadata_items FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON doc_dg_metadata_items
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)

    # 2. doc_dg_document_versions
    op.add_column('doc_dg_document_versions', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("""
        UPDATE doc_dg_document_versions v
        SET tenant_id = d.tenant_id
        FROM doc_dg_documents d
        WHERE v.document_id = d.id
    """)
    op.alter_column('doc_dg_document_versions', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_doc_dg_document_versions_tenant', 'doc_dg_document_versions', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_index('idx_doc_dg_document_versions_tenant_id', 'doc_dg_document_versions', ['tenant_id'])

    op.execute("ALTER TABLE doc_dg_document_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_document_versions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON doc_dg_document_versions
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)

    # 3. doc_dg_templates (supports global templates with NULL tenant_id or tenant-specific templates)
    op.add_column('doc_dg_templates', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_doc_dg_templates_tenant', 'doc_dg_templates', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_index('idx_doc_dg_templates_tenant_id', 'doc_dg_templates', ['tenant_id'])

    op.execute("ALTER TABLE doc_dg_templates ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_templates FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON doc_dg_templates
        USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)

    # 4. sys_dg_retention_classes (supports global classes with NULL tenant_id or tenant-specific retention classes)
    op.add_column('sys_dg_retention_classes', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_sys_dg_retention_classes_tenant', 'sys_dg_retention_classes', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_index('idx_sys_dg_retention_classes_tenant_id', 'sys_dg_retention_classes', ['tenant_id'])

    op.execute("ALTER TABLE sys_dg_retention_classes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sys_dg_retention_classes FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON sys_dg_retention_classes
        USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)


def downgrade() -> None:
    # 4. sys_dg_retention_classes
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON sys_dg_retention_classes")
    op.execute("ALTER TABLE sys_dg_retention_classes NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sys_dg_retention_classes DISABLE ROW LEVEL SECURITY")
    op.drop_index('idx_sys_dg_retention_classes_tenant_id', table_name='sys_dg_retention_classes')
    op.drop_constraint('fk_sys_dg_retention_classes_tenant', 'sys_dg_retention_classes', type_='foreignkey')
    op.drop_column('sys_dg_retention_classes', 'tenant_id')

    # 3. doc_dg_templates
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON doc_dg_templates")
    op.execute("ALTER TABLE doc_dg_templates NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_templates DISABLE ROW LEVEL SECURITY")
    op.drop_index('idx_doc_dg_templates_tenant_id', table_name='doc_dg_templates')
    op.drop_constraint('fk_doc_dg_templates_tenant', 'doc_dg_templates', type_='foreignkey')
    op.drop_column('doc_dg_templates', 'tenant_id')

    # 2. doc_dg_document_versions
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON doc_dg_document_versions")
    op.execute("ALTER TABLE doc_dg_document_versions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_document_versions DISABLE ROW LEVEL SECURITY")
    op.drop_index('idx_doc_dg_document_versions_tenant_id', table_name='doc_dg_document_versions')
    op.drop_constraint('fk_doc_dg_document_versions_tenant', 'doc_dg_document_versions', type_='foreignkey')
    op.drop_column('doc_dg_document_versions', 'tenant_id')

    # 1. doc_dg_metadata_items
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON doc_dg_metadata_items")
    op.execute("ALTER TABLE doc_dg_metadata_items NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_metadata_items DISABLE ROW LEVEL SECURITY")
    op.drop_index('idx_doc_dg_metadata_items_tenant_id', table_name='doc_dg_metadata_items')
    op.drop_constraint('fk_doc_dg_metadata_items_tenant', 'doc_dg_metadata_items', type_='foreignkey')
    op.drop_column('doc_dg_metadata_items', 'tenant_id')
