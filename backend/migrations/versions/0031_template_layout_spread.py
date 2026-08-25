"""T26 — template layout column, spread-register support

Adds doc_dg_templates.layout ('single_page' default, or 'spread' for a
register whose entries run across two facing pages). Wiring for
join_spread() (already built and unit-tested, never called anywhere)
lives in vlm_extraction.py; this is the template-level flag that opts a
form into it. The left/right field convention this pairs with is a
best-effort invention, not modeled on a real scanned spread — no seeded
template exists yet (T25 stays blocked on A1) — flagged for
revalidation once a real reference corpus is available.

Revision ID: 0031_template_layout_spread
Revises: 0030_trigram_threshold_config
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0031_template_layout_spread'
down_revision: Union[str, None] = '0030_trigram_threshold_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'doc_dg_templates',
        sa.Column('layout', sa.Text(), nullable=False, server_default='single_page'),
    )
    op.create_check_constraint(
        'ck_doc_dg_templates_layout',
        'doc_dg_templates',
        "layout IN ('single_page', 'spread')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_doc_dg_templates_layout', 'doc_dg_templates', type_='check')
    op.drop_column('doc_dg_templates', 'layout')
