"""T03 — seed search_relevance_fallback_ratio.

Real gap found live 2026-09-10 during an end-to-end product review: the
near-miss relevance fallback added 2026-09-09 (search_service.py's
_select_relevant_ranks, fixing the "no matching documents" flakiness bug
from the verification report) reads this threshold via
config_service.get_float(..., 0.5) but nothing had ever migrated it into
sys_dg_config — so it silently only ever ran on the Python-literal
default, invisible and uneditable in the T03 admin Settings screen,
breaking this codebase's own "thresholds live in sys_dg_config, not in
code" contract (see DEVELOPER_BRIEF.md §3.5). Seed value matches exactly
what the code already used — this migration changes no behaviour, only
where the number lives, same as 0041's own stated pattern.

Revision ID: 0051_relevance_fallback_ratio
Revises: 0050_enable_rls_missing_tables
Create Date: 2026-09-10 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Kept short deliberately: alembic_version.version_num is varchar(32), and
# the first attempt at this migration ('0051_search_relevance_fallback_
# threshold', 40 chars) failed the version bump with
# StringDataRightTruncationError after the seed insert had already run --
# alembic runs the whole migration in one transaction, so it rolled back
# cleanly, but any revision id for this table needs to fit the column.
revision: str = '0051_relevance_fallback_ratio'
down_revision: Union[str, None] = '0050_enable_rls_missing_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_VALUES = [
    ('search_relevance_fallback_ratio', 0.5, "search_service._select_relevant_ranks: when nothing crosses search_relevance_threshold, the single best candidate is still returned if its score >= search_relevance_threshold * this ratio, instead of 'no matching documents' -- fixes ordinary reranker score sensitivity flipping a genuinely relevant borderline result to nothing between two near-identical queries."),
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
    op.execute("DELETE FROM sys_dg_config WHERE key IN ('search_relevance_fallback_ratio')")
