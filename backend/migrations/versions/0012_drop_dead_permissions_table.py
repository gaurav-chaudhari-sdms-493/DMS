"""T34 — drop iam_dg_permissions: zero code references, not real access control

Confirmed by direct grep across app/ and tests/: nothing reads or writes
this table. Keeping it risked being mistaken for working access control.
Real permissions return with T50 (RBAC for six personas), once D-1
(nested folders) is resolved and T50 defines what a permission actually
needs to look like — this table's shape was never validated against
that and shouldn't be resurrected as-is.

Revision ID: 0012_drop_dead_permissions_table
Revises: 0011_doc_dg_templates
Create Date: 2026-08-24 00:00:04.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0012_drop_dead_permissions_table'
down_revision: Union[str, None] = '0011_doc_dg_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('iam_dg_permissions')


def downgrade() -> None:
    op.create_table(
        'iam_dg_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_iam_dg_permissions_user', 'iam_dg_permissions', 'iam_dg_users', ['user_id'], ['id'])
    op.create_index('idx_iam_dg_permissions_user_id', 'iam_dg_permissions', ['user_id'])
