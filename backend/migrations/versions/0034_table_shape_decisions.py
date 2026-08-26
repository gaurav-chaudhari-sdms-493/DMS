"""TS1 — doc_dg_table_shape_decisions: cached vertical/horizontal
adjudication verdicts, keyed by table-fragment SHAPE (which fields each
side carries), not by document — so a recurring register form asks the
adjudicator (or a human, once TS4 wires review in) once, not once per
occurrence. See app/pipeline/table_stitch.py:shape_hash().

Revision ID: 0034_table_shape_decisions
Revises: 0033_licensing
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0034_table_shape_decisions'
down_revision: Union[str, None] = '0033_licensing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'doc_dg_table_shape_decisions',
        sa.Column('shape_hash', sa.String(length=64), primary_key=True),
        sa.Column('relation', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('decided_by', sa.String(), nullable=False),
        sa.Column('decided_by_actor_id', UUID(as_uuid=True), sa.ForeignKey('iam_dg_users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_doc_dg_table_shape_decisions_relation',
        'doc_dg_table_shape_decisions',
        "relation IN ('vertical', 'horizontal', 'unrelated')",
    )
    op.create_check_constraint(
        'ck_doc_dg_table_shape_decisions_decided_by',
        'doc_dg_table_shape_decisions',
        "decided_by IN ('evidence', 'llm', 'human')",
    )


def downgrade() -> None:
    op.drop_table('doc_dg_table_shape_decisions')
