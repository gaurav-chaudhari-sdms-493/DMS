"""add_folders_and_drive_fields

Revision ID: c1a2b3c4d5e6
Revises: 27e405dd516b
Create Date: 2026-07-22 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1a2b3c4d5e6'
down_revision: Union[str, None] = '27e405dd516b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create folders table
    op.create_table(
        'folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_starred', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_trashed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('trashed_at', sa.DateTime(), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True, server_default='#1a73e8')
    )
    op.create_index(op.f('ix_folders_parent_id'), 'folders', ['parent_id'], unique=False)
    op.create_index(op.f('ix_folders_tenant_id'), 'folders', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_folders_created_by'), 'folders', ['created_by'], unique=False)

    # 2. Add columns to documents table
    op.add_column('documents', sa.Column('folder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id', ondelete='SET NULL'), nullable=True))
    op.add_column('documents', sa.Column('is_starred', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('documents', sa.Column('is_trashed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('documents', sa.Column('trashed_at', sa.DateTime(), nullable=True))
    
    op.create_index(op.f('ix_documents_folder_id'), 'documents', ['folder_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_folder_id'), table_name='documents')
    op.drop_column('documents', 'trashed_at')
    op.drop_column('documents', 'is_trashed')
    op.drop_column('documents', 'is_starred')
    op.drop_column('documents', 'folder_id')

    op.drop_index(op.f('ix_folders_created_by'), table_name='folders')
    op.drop_index(op.f('ix_folders_tenant_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_parent_id'), table_name='folders')
    op.drop_table('folders')
