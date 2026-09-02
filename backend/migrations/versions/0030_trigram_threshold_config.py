"""T72 — the pg_trgm leg's threshold, in config from day one (T03's own rule)

word_similarity's default GUC (0.6) is tuned for short-string-to-short-
string comparison and misses realistic typos against a long chunk (a
one-character-swap typo like "Depshmukh" vs "Deshmukh" scores ~0.58,
verified live) — 0.3 is deliberately looser, matching the 'S' size of
this task rather than a tuned-against-a-real-corpus number.

Revision ID: 0030_trigram_threshold_config
Revises: 0029_trigram_search_index
Create Date: 2026-08-25 00:00:01.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0030_trigram_threshold_config'
down_revision: Union[str, None] = '0029_trigram_search_index'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    table = sa.table(
        'sys_dg_config',
        sa.column('key', sa.String()),
        sa.column('value', postgresql.JSONB()),
        sa.column('description', sa.Text()),
    )
    op.bulk_insert(table, [
        {
            'key': 'search_trigram_threshold',
            'value': {'v': 0.3},
            'description': "Minimum word_similarity() score for the fuzzy/trigram search leg (T72) — looser than pg_trgm's own 0.6 GUC default so realistic single-typo misspellings still match.",
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM sys_dg_config WHERE key = 'search_trigram_threshold'")
