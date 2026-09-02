"""T24 — template registry: form type x era, field definitions + per-field validation

Global table, not tenant-scoped — a form's layout doesn't vary per tenant,
so no RLS policy here (consistent with sys_dg_config).

Revision ID: 0011_doc_dg_templates
Revises: 0010_pages_facts_regions
Create Date: 2026-08-24 00:00:03.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0011_doc_dg_templates'
down_revision: Union[str, None] = '0010_pages_facts_regions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doc_dg_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('form_type', sa.String(), nullable=False),
        sa.Column('era_label', sa.String(), nullable=False),
        sa.Column('field_schema', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('form_type', 'era_label', name='uq_doc_dg_templates_form_era'),
    )
    op.create_index('idx_doc_dg_templates_form_type', 'doc_dg_templates', ['form_type'])


def downgrade() -> None:
    op.drop_table('doc_dg_templates')
