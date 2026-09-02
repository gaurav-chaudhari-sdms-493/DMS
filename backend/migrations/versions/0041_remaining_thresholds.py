"""T03 — move the last hardcoded thresholds into sys_dg_config.

The original backlog's six thresholds (relevance, RRF k, chunk size/
overlap, embed batch, retention days, candidate limits) were already
seeded in 0009/0028/0030. This migration closes the remaining gap found
during the 2026-09-01 re-audit: TS1's table-stitch decision thresholds
and T79's fuzzy-duplicate similarity threshold were still literals in
their modules. Seed values match exactly what the code already used —
this migration changes no behaviour, only where the numbers live.

Revision ID: 0041_remaining_thresholds
Revises: 0040_entity_dedup_threshold
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0041_remaining_thresholds'
down_revision: Union[str, None] = '0040_entity_dedup_threshold'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_VALUES = [
    ('table_stitch_vertical_similarity_threshold', 0.7, "TS1 table_stitch.decide_relation: minimum Jaccard similarity between two page fragments' field-name sets to call them the same table continuing vertically."),
    ('table_stitch_horizontal_min_coverage', 0.5, "TS1 table_stitch.decide_relation: minimum combined template-field coverage for two disjoint field-name sets to be called horizontal column bands of one row."),
    ('table_stitch_adjudication_confidence_threshold', 0.6, "TS1 vlm_extraction: minimum LLM adjudication confidence to accept its vertical/horizontal verdict instead of flagging the page pair as stitch-ambiguous for human review."),
    ('duplicate_fuzzy_similarity_threshold', 0.92, "T79 duplicate_service.find_fuzzy_duplicates: minimum cosine similarity between two documents' first-chunk embeddings to surface as a possible rescan/duplicate."),
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
    op.execute(
        "DELETE FROM sys_dg_config WHERE key IN ("
        "'table_stitch_vertical_similarity_threshold', "
        "'table_stitch_horizontal_min_coverage', "
        "'table_stitch_adjudication_confidence_threshold', "
        "'duplicate_fuzzy_similarity_threshold')"
    )
