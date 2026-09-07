"""Row-grouping bug fix — doc_dg_facts.row_group_id

Real bug found live 2026-09-07 (Wardha.pdf's table view): no row identity
was ever stored for extracted facts, so fact_service.py's table-view
endpoint had to reconstruct rows by clustering FactRegion.y0 alone, with
a fixed tolerance and no x0 disambiguation at all. Broke badly on any
page laid out as side-by-side entry-columns (each entry's own fields
span nearly the full page height there, while unrelated entries' same-
named fields land on the same y-band) -- one entry's worth of fields
exploded into many near-empty rows, and unrelated entries' same-named
fields silently overwrote each other (7 of every 8 real values lost on
the affected page).

This column lets vlm_extraction.py record the real row grouping it
already knows at write time (one merged_row / one result.pairs entry),
so get_table_view_for_document can group by it directly instead of
guessing. Nullable and un-backfillable on purpose: which facts belonged
to the same row is genuinely unrecoverable for documents already
extracted before this column existed -- those keep falling back to the
old (unchanged) heuristic, this only fixes it going forward.

Revision ID: 0048_fact_row_group_id
Revises: 0047_metadata_item_regions
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0048_fact_row_group_id'
down_revision: Union[str, None] = '0047_metadata_item_regions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_facts', sa.Column('row_group_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('idx_doc_dg_facts_row_group_id', 'doc_dg_facts', ['row_group_id'])


def downgrade() -> None:
    op.drop_index('idx_doc_dg_facts_row_group_id', table_name='doc_dg_facts')
    op.drop_column('doc_dg_facts', 'row_group_id')
