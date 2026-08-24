"""T23 — document classification stage + unclassified queue

Persists what T22's select_template_for_document() previously only
computed ad-hoc and threw away. classification_status defaults to
'unclassified' — most documents in this system are not statutory forms at
all (budgets, financial analyses, etc.) and never will be, so
'unclassified' is a normal resting state an operator can dismiss, not an
error state.

Revision ID: 0025_document_classification
Revises: 0024_retention_classes
Create Date: 2026-08-24 00:00:13.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0025_document_classification'
down_revision: Union[str, None] = '0024_retention_classes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'doc_dg_documents',
        sa.Column('classification_status', sa.Text(), nullable=False, server_default='unclassified'),
    )
    op.create_check_constraint(
        'ck_doc_dg_documents_classification_status',
        'doc_dg_documents',
        "classification_status IN ('unclassified', 'classified', 'dismissed')",
    )
    op.add_column(
        'doc_dg_documents',
        sa.Column('matched_template_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_doc_dg_documents_matched_template', 'doc_dg_documents', 'doc_dg_templates',
        ['matched_template_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(
        'idx_doc_dg_documents_classification_status', 'doc_dg_documents',
        ['tenant_id', 'classification_status'],
    )


def downgrade() -> None:
    op.drop_index('idx_doc_dg_documents_classification_status', table_name='doc_dg_documents')
    op.drop_constraint('fk_doc_dg_documents_matched_template', 'doc_dg_documents', type_='foreignkey')
    op.drop_column('doc_dg_documents', 'matched_template_id')
    op.drop_constraint('ck_doc_dg_documents_classification_status', 'doc_dg_documents', type_='check')
    op.drop_column('doc_dg_documents', 'classification_status')
