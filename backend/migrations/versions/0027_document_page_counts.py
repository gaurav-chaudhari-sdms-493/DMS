"""T76 — page counts on documents, for the completeness dashboard's
"failed pages" metric.

T33 already fixes the extraction_failed *flag* on each page dict during
OCR, but that flag lived only in memory for the duration of one ingestion
task — nothing persisted it anywhere. doc_dg_pages (T04-06) only gets
rows for documents that matched a template and went through T22's VLM
extraction, which is a small minority of documents; a dashboard metric
needs something every ingested document has, not just template matches.
These two counters are populated once at ingest, for every document,
regardless of whether it ever matches a template.

Revision ID: 0027_document_page_counts
Revises: 0026_fact_verification
Create Date: 2026-08-24 00:00:15.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0027_document_page_counts'
down_revision: Union[str, None] = '0026_fact_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_documents', sa.Column('pages_total_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('doc_dg_documents', sa.Column('pages_failed_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('doc_dg_documents', 'pages_failed_count')
    op.drop_column('doc_dg_documents', 'pages_total_count')
