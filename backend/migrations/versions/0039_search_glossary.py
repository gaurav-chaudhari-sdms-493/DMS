"""TS7 — sys_dg_search_glossary: cross-script domain-vocabulary synonym
groups for search query expansion.

Free and local, checked before/alongside the existing LLM-based
trilingual query expansion (search_service.py:_expand_trilingual_query),
not instead of it. That existing expansion already runs an LLM call on
every search unconditionally, and degrades to the RAW query verbatim on
any failure — including in air-gapped mode with no local LLM
(app/ai/airgapped.py's enforce_local() gate). This glossary fills
exactly that gap for known domain vocabulary: a free, always-available,
deterministic cross-script match that works even when the LLM path is
unavailable, and guarantees the exact indexed term for known vocabulary
rather than relying on a general-purpose model to translate correctly.

Terms are grouped by canonical_key; every row sharing a canonical_key is
a synonym of every other row in that group. Seed vocabulary below is
independently curated from terms directly observed in real waqf-register
documents processed this session (not copied from any reference
project) — e.g. "mutawalli", "gunthas", "mouje" all appear verbatim in
the real 1973 Maharashtra State Board of Waqfs gazette table used to
test TS1/TS2/TS5.

Revision ID: 0039_search_glossary
Revises: 0038_page_furniture
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0039_search_glossary'
down_revision: Union[str, None] = '0038_page_furniture'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# canonical_key -> [terms...], each term lowercased (lookup is case-insensitive
# by storing lowercase; search_glossary_service.py lowercases the query side too)
SEED_GROUPS = {
    "waqf": ["waqf", "wakf", "वक्फ"],
    "graveyard": ["graveyard", "kabrastan", "qabrastan", "कब्रस्तान"],
    "mutawalli": ["mutawalli", "mutawali", "मुतवली"],
    "survey number": ["survey number", "survey no", "s no", "सर्वे नंबर", "सर्वे नं"],
    "gat number": ["gat no", "gat number", "गट नं", "गट नंबर"],
    "village": ["village", "mouje", "मौजे", "गाव"],
    "taluka": ["taluka", "tehsil", "तालुका"],
    "district": ["district", "jilha", "जिल्हा"],
    "guntha": ["guntha", "gunthas", "गुंठे", "गुंठा"],
    "valuation": ["valuation", "किंमत", "मूल्य"],
    "boundary": ["boundary", "chatusima", "चतु:सीमा", "सीमा"],
    "registration": ["registration", "nondani", "नोंदणी"],
    "certificate": ["certificate", "praman patra", "प्रमाणपत्र"],
    "khatedar": ["khatedar", "owner", "खातेदार"],
    "sunni": ["sunni", "सुन्नी"],
    "shia": ["shia", "शिया"],
}


def upgrade() -> None:
    op.create_table(
        'sys_dg_search_glossary',
        sa.Column('term', sa.String(), primary_key=True),
        sa.Column('canonical_key', sa.String(), nullable=False),
    )
    op.create_index('idx_sys_dg_search_glossary_canonical_key', 'sys_dg_search_glossary', ['canonical_key'])

    table = sa.table(
        'sys_dg_search_glossary',
        sa.column('term', sa.String()),
        sa.column('canonical_key', sa.String()),
    )
    rows = [
        {"term": term.lower(), "canonical_key": canonical_key}
        for canonical_key, terms in SEED_GROUPS.items()
        for term in terms
    ]
    op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_index('idx_sys_dg_search_glossary_canonical_key', table_name='sys_dg_search_glossary')
    op.drop_table('sys_dg_search_glossary')
