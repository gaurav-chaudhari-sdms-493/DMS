"""fix audit_log column mismatch with ORM model

Revision ID: 0004_fix_audit_log_columns
Revises: 0003_enable_rls
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_fix_audit_log_columns'
down_revision: Union[str, None] = '0003_enable_rls'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('audit_logs', 'actor_user_id', new_column_name='actor_id')
    op.add_column('audit_logs', sa.Column('resource_type', sa.String(), nullable=True))
    op.add_column('audit_logs', sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.String(), nullable=True))
    op.execute("ALTER INDEX ix_audit_logs_actor_user_id RENAME TO ix_audit_logs_actor_id")


def downgrade() -> None:
    op.execute("ALTER INDEX ix_audit_logs_actor_id RENAME TO ix_audit_logs_actor_user_id")
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'resource_id')
    op.drop_column('audit_logs', 'resource_type')
    op.alter_column('audit_logs', 'actor_id', new_column_name='actor_user_id')
