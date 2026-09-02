"""TS4 — doc_dg_field_trust_signal: generalizes TS1's "ask once per kind
of ambiguity" pattern to the low_confidence adjudication queue.

Deliberately informational, not auto-promoting: T55's hard rule ("no
promotion to verified without an actor event") stays intact — a real
human still confirms every fact via confirm_fact/bulk_confirm_facts.
This table only accumulates how often a given field_name has
historically been confirmed-as-correct vs corrected-as-wrong at low
confidence, surfaced as a hint on the adjudication queue so a reviewer
sees "this field type has checked out 12/12 times before" instead of
evaluating each occurrence with zero context.

Keyed by field_name alone (not (template, field_name)) as a deliberate
simplification: Fact doesn't store which template it came from directly
(only reachable via a Document join), and this is an informational hint
feeding a queue view, not a data-correctness decision like TS1's table
relation cache — a field_name collision across two different templates
is a minor precision loss, not a data-integrity risk.

Revision ID: 0037_field_trust_signal
Revises: 0036_extraction_archive
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0037_field_trust_signal'
down_revision: Union[str, None] = '0036_extraction_archive'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doc_dg_field_trust_signal',
        sa.Column('field_name', sa.String(), primary_key=True),
        sa.Column('confirmed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('corrected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('doc_dg_field_trust_signal')
