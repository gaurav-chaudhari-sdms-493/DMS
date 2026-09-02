"""T75 — Devanagari indexing correctness: a second tsvector on the 'simple' config

The existing content_tsv column is generated with to_tsvector('english', ...),
but the query side falls through to plainto_tsquery('simple', ...) for Marathi
variants. English config applies stemming + stopword removal; simple doesn't
— matching a 'simple' query against an 'english' vector silently breaks
stemmed English matches and gives Devanagari content no config actually
tuned for it. Add a second generated column on 'simple' and search both.

Revision ID: 0013_devanagari_tsvector
Revises: 0012_drop_dead_permissions_table
Create Date: 2026-08-24 00:00:05.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0013_devanagari_tsvector'
down_revision: Union[str, None] = '0012_drop_dead_permissions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE doc_dg_chunks
        ADD COLUMN IF NOT EXISTS content_tsv_simple tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_doc_dg_chunks_content_tsv_simple ON doc_dg_chunks USING GIN (content_tsv_simple)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_dg_chunks_content_tsv_simple")
    op.execute("ALTER TABLE doc_dg_chunks DROP COLUMN IF EXISTS content_tsv_simple")
