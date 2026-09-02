"""fix folders/permissions/chat_sessions/chat_messages column mismatch with ORM models

Revision ID: 0006_fix_folder_chat_perm_cols
Revises: 0005_fix_document_columns
Create Date: 2026-08-21 00:00:01.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006_fix_folder_chat_perm_cols'
down_revision: Union[str, None] = '0005_fix_document_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # folders: model expects these, baseline migration never created them
    op.add_column('folders', sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('folders', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('folders', sa.Column('is_starred', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('folders', sa.Column('trashed_at', sa.DateTime(), nullable=True))
    op.add_column('folders', sa.Column('color', sa.String(length=50), nullable=True, server_default='#1a73e8'))
    op.create_index('ix_folders_created_by', 'folders', ['created_by'])

    # chat_sessions: model expects an onupdate-tracked updated_at column
    op.add_column('chat_sessions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # chat_messages: model stores per-turn search context the baseline migration omitted
    op.add_column('chat_messages', sa.Column('results', postgresql.JSONB(), nullable=True))
    op.add_column('chat_messages', sa.Column('filters', postgresql.JSONB(), nullable=True))

    # permissions: unused by any current code path (verified), but the migration's
    # document-specific shape (document_id/permission_level) doesn't match the model's
    # generic resource_type/resource_id/action shape. Realign to the model.
    op.drop_column('permissions', 'document_id')
    op.drop_column('permissions', 'permission_level')
    op.add_column('permissions', sa.Column('resource_type', sa.String(), nullable=False))
    op.add_column('permissions', sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column('permissions', sa.Column('action', sa.String(), nullable=False))


def downgrade() -> None:
    op.drop_column('permissions', 'action')
    op.drop_column('permissions', 'resource_id')
    op.drop_column('permissions', 'resource_type')
    op.add_column('permissions', sa.Column('permission_level', sa.String(), nullable=False))
    op.add_column('permissions', sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False))

    op.drop_column('chat_messages', 'filters')
    op.drop_column('chat_messages', 'results')

    op.drop_column('chat_sessions', 'updated_at')

    op.drop_index('ix_folders_created_by', table_name='folders')
    op.drop_column('folders', 'color')
    op.drop_column('folders', 'trashed_at')
    op.drop_column('folders', 'is_starred')
    op.drop_column('folders', 'updated_at')
    op.drop_column('folders', 'created_by')
