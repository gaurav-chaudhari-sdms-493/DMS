"""seed the last hardcoded threshold T03 called out — embedding batch size

T03 — Build Design v0.3 Section 12: relevance/RRF/chunk/retention/candidate
limits already moved to sys_dg_config in 0009; "embed batch" was the one
left behind. Two keys, not one — OpenAIEmbeddingProvider's request batching
(payload/rate-limit driven, was hardcoded to 100) and BGEM3EmbeddingProvider's
local SentenceTransformer batching (GPU/CPU memory driven, was an invisible
default of 32 baked into the encode() call) are different concerns with
different natural defaults, so they get their own keys rather than sharing
one number that would be wrong for one of the two providers.

Revision ID: 0028_embed_batch_size_config
Revises: 0027_document_page_counts
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0028_embed_batch_size_config'
down_revision: Union[str, None] = '0027_document_page_counts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_VALUES = [
    ('embed_api_batch_size', 100, 'Texts per request when embedding via an API provider (OpenAI) — payload/rate-limit driven.'),
    ('embed_local_batch_size', 32, 'Texts per encode() call for the local BGE-M3 model — GPU/CPU memory driven.'),
]


def upgrade() -> None:
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
    op.execute("DELETE FROM sys_dg_config WHERE key IN ('embed_api_batch_size', 'embed_local_batch_size')")
