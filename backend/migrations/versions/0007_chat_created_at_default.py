"""add missing server_default now() to chat_sessions/chat_messages.created_at

The ORM models declare server_default=func.now() on these columns, but the
baseline migration only ever set NOT NULL with no default — so the ORM
(trusting the model) omits created_at from every INSERT, and Postgres has
no default to fall back on. Same drift-bug class as migrations 0004-0006,
different symptom (missing default instead of missing column).

Revision ID: 0007_chat_created_at_default
Revises: 0006_fix_folder_chat_perm_cols
Create Date: 2026-08-21 00:00:02.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_chat_created_at_default'
down_revision: Union[str, None] = '0006_fix_folder_chat_perm_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('chat_sessions', 'created_at', server_default=sa.func.now())
    op.alter_column('chat_messages', 'created_at', server_default=sa.func.now())


def downgrade() -> None:
    op.alter_column('chat_messages', 'created_at', server_default=None)
    op.alter_column('chat_sessions', 'created_at', server_default=None)
