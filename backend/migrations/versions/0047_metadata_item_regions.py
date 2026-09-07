"""T05 — source-location coverage for non-VLM (metadata) facts

chunker.py/extractor.py already compute word-level bbox regions per page
(normalised 0-1, top-left origin, same contract as T06's FactRegion) and
carry them all the way to doc_dg_chunks.chunk_metadata -- but nothing ever
reads them back out to say where a given `doc_dg_metadata_items` value
actually came from on the page. This adds doc_dg_metadata_item_regions,
the metadata-item equivalent of doc_dg_fact_regions.

Decoupled from doc_dg_pages on purpose: that table is only ever written by
the VLM/T22 classification path (see worker.py's own comment — "unlike
doc_dg_pages, which only T22 writes to"), so most documents (anything that
never matched a classification template) have zero doc_dg_pages rows.
Metadata extraction runs on every document regardless of classification,
so this uses a plain page_number column instead of a doc_dg_pages FK.

No "must have at least one region" trigger here (unlike T06's facts) —
a metadata value legitimately may not be locatable (LLM paraphrase,
reformatting, a value spanning a page break), and no region is a more
honest result than a fabricated one.

Revision ID: 0047_metadata_item_regions
Revises: 0046_restricted_app_role
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0047_metadata_item_regions'
down_revision: Union[str, None] = '0046_restricted_app_role'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doc_dg_metadata_item_regions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metadata_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('x0', sa.Float(), nullable=False),
        sa.Column('y0', sa.Float(), nullable=False),
        sa.Column('x1', sa.Float(), nullable=False),
        sa.Column('y1', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key(
        'fk_doc_dg_metadata_item_regions_tenant',
        'doc_dg_metadata_item_regions', 'iam_dg_tenants', ['tenant_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_doc_dg_metadata_item_regions_item',
        'doc_dg_metadata_item_regions', 'doc_dg_metadata_items', ['metadata_item_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'idx_doc_dg_metadata_item_regions_tenant_id', 'doc_dg_metadata_item_regions', ['tenant_id'],
    )
    op.create_index(
        'idx_doc_dg_metadata_item_regions_item_id', 'doc_dg_metadata_item_regions', ['metadata_item_id'],
    )

    op.execute("ALTER TABLE doc_dg_metadata_item_regions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_metadata_item_regions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON doc_dg_metadata_item_regions
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON doc_dg_metadata_item_regions")
    op.execute("ALTER TABLE doc_dg_metadata_item_regions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE doc_dg_metadata_item_regions DISABLE ROW LEVEL SECURITY")
    op.drop_table('doc_dg_metadata_item_regions')
