"""T20/D-5 — real per-field confidence status on facts

Adds doc_dg_facts.status, populated by the D-5 confidence-band policy
(app/services/template_service.py: classify_confidence) at write time —
'machine' when a field's VLM-reported confidence clears its template's
auto_commit band (or the conservative global default), 'in_review'
otherwise. 'verified' is reserved for the (not yet built, T51) human
promotion step; nothing writes it yet.

Revision ID: 0023_fact_confidence_status
Revises: 0022_personas_departments
Create Date: 2026-08-24 00:00:11.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0023_fact_confidence_status'
down_revision: Union[str, None] = '0022_personas_departments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'doc_dg_facts',
        sa.Column('status', sa.Text(), nullable=False, server_default='machine'),
    )
    op.create_check_constraint(
        'ck_doc_dg_facts_status',
        'doc_dg_facts',
        "status IN ('machine', 'in_review', 'verified')",
    )
    op.create_index('idx_doc_dg_facts_status', 'doc_dg_facts', ['tenant_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_doc_dg_facts_status', table_name='doc_dg_facts')
    op.drop_constraint('ck_doc_dg_facts_status', 'doc_dg_facts', type_='check')
    op.drop_column('doc_dg_facts', 'status')
