"""T56 — track who confirmed an edge, separate from who created it

A human can create a tier-3/4 edge directly and it still needs its own
confirmation event before counting as verified evidence, same as a
machine-extracted one does — creation and confirmation are different
facts and need different actor columns.

Revision ID: 0015_entity_edge_confirmation
Revises: 0014_entity_graph
Create Date: 2026-08-24 00:00:07.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0015_entity_edge_confirmation'
down_revision: Union[str, None] = '0014_entity_graph'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('entity_dg_edges', sa.Column('verified_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('entity_dg_edges', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_entity_dg_edges_verified_by', 'entity_dg_edges', 'iam_dg_users', ['verified_by_actor_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_entity_dg_edges_verified_by', 'entity_dg_edges', type_='foreignkey')
    op.drop_column('entity_dg_edges', 'verified_at')
    op.drop_column('entity_dg_edges', 'verified_by_actor_id')
