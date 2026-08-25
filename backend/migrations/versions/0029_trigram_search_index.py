"""T72 — the pg_trgm leg: index exists as an extension since 0001, never used

Adds the GIN trigram index search_service.py's new fuzzy-match leg needs
(gin_trgm_ops supports both '%'/similarity and '<%'/word_similarity —
verified against the running DB: a forced-index EXPLAIN shows the planner
using this index for '<%', not a raw function scan). No new config table
row for the threshold — that's seeded in 0009's style by 0030 alongside
this, kept as a separate concern from the index itself.

Revision ID: 0029_trigram_search_index
Revises: 0028_embed_batch_size_config
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0029_trigram_search_index'
down_revision: Union[str, None] = '0028_embed_batch_size_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_doc_dg_chunks_content_trgm ON doc_dg_chunks USING GIN (content gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_dg_chunks_content_trgm")
