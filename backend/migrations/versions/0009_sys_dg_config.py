"""create sys_dg_config and seed it with today's hardcoded thresholds

T02 — Build Design v0.3 Section 12: every threshold and limit in one place,
with documented defaults, rather than a literal buried in a service file.
Seed values match exactly what the code already used, so this migration
changes nothing about current behaviour — only where the numbers live.

Revision ID: 0009_sys_dg_config
Revises: 0008_dg_naming_standard
Create Date: 2026-08-24 00:00:01.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0009_sys_dg_config'
down_revision: Union[str, None] = '0008_dg_naming_standard'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_VALUES = [
    ('search_rrf_k', 60, 'Reciprocal Rank Fusion constant used to merge vector and keyword search legs.'),
    ('search_relevance_threshold', 0.15, 'Minimum fused relevance score a result must clear to be returned.'),
    ('search_candidate_limit', 20, 'Max candidate rows pulled per search leg (vector, keyword) before fusion.'),
    ('search_cache_ttl_seconds', 300, 'How long a search response is cached before re-querying.'),
    ('search_pending_docs_preview_limit', 3, 'Max titles listed when telling a user documents are still indexing.'),
    ('chunk_size_tokens', 512, 'Target token count per chunk when splitting extracted document text.'),
    ('chunk_overlap_tokens', 64, 'Token overlap between consecutive chunks.'),
    ('trash_retention_days', 30, 'Days a trashed document/folder is kept before permanent purge.'),
    ('default_extraction_confidence', 0.9, 'Confidence score recorded for LLM-extracted metadata fields.'),
]


def upgrade() -> None:
    op.create_table(
        'sys_dg_config',
        sa.Column('key', sa.String(), primary_key=True),
        sa.Column('value', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    table = sa.table(
        'sys_dg_config',
        sa.column('key', sa.String()),
        sa.column('value', postgresql.JSONB()),
        sa.column('description', sa.Text()),
    )
    op.bulk_insert(table, [
        {'key': key, 'value': {'v': value}, 'description': description}
        for key, value, description in SEED_VALUES
    ])


def downgrade() -> None:
    op.drop_table('sys_dg_config')
