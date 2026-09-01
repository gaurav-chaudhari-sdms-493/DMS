"""Entity-graph accuracy — config threshold for fuzzy duplicate-node
detection (entity_graph_service.find_similar_nodes).

pg_trgm's similarity() (not word_similarity(), which is for a short query
against a long document — the T72 search leg's use case) is the right
function for comparing two short, comparable-length strings like two
entity labels head-to-head. 0.45 is deliberately looser than pg_trgm's
own 0.3 default GUC would suggest as "unrelated" and tighter than a
guess-anything bar: verified live against pairs actually seen this
session — "Shri Juni Masjid, Hirpur" vs "Shri Juni Masjid, Village.
Hirpur, Taluka. Murtizapur" (the same institution, read off two different
pages of the same real document) scores ~0.5, while two different common
Marathi/English surnames a few characters apart ("Deshmukh" vs "Deshpande")
score well under 0.3 — so 0.45 catches the former as a real duplicate
candidate without flagging the latter.

Revision ID: 0040_entity_dedup_threshold
Revises: 0039_search_glossary
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0040_entity_dedup_threshold'
down_revision: Union[str, None] = '0039_search_glossary'
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
            'key': 'entity_dedup_similarity_threshold',
            'value': {'v': 0.45},
            'description': "Minimum pg_trgm similarity() score between two same-type entity labels to surface as a possible-duplicate candidate on node creation.",
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM sys_dg_config WHERE key = 'entity_dedup_similarity_threshold'")
