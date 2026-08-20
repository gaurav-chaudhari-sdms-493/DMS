"""fix documents/document_versions column mismatch with ORM models

Revision ID: 0005_fix_document_columns
Revises: 0004_fix_audit_log_columns
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005_fix_document_columns'
down_revision: Union[str, None] = '0004_fix_audit_log_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # documents: add columns the ORM model expects but the baseline migration never created
    op.add_column('documents', sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('documents', sa.Column('doc_type', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('is_starred', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('documents', sa.Column('trashed_at', sa.DateTime(), nullable=True))
    op.create_index('ix_documents_created_by', 'documents', ['created_by'])

    # documents: columns the migration created that the ORM model never mapped —
    # ORM inserts omit them entirely, so NOT NULL with no default breaks every insert
    op.alter_column('documents', 'mime_type', nullable=True)
    op.alter_column('documents', 'updated_at', nullable=True)

    # document_versions: same class of missing columns
    op.add_column('document_versions', sa.Column('file_hash', sa.String(), nullable=True))
    op.add_column('document_versions', sa.Column('original_filename', sa.String(), nullable=True))
    op.add_column('document_versions', sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.create_index('ix_document_versions_uploaded_by', 'document_versions', ['uploaded_by'])


def downgrade() -> None:
    op.drop_index('ix_document_versions_uploaded_by', table_name='document_versions')
    op.drop_column('document_versions', 'uploaded_by')
    op.drop_column('document_versions', 'original_filename')
    op.drop_column('document_versions', 'file_hash')

    op.alter_column('documents', 'updated_at', nullable=False)
    op.alter_column('documents', 'mime_type', nullable=False)

    op.drop_index('ix_documents_created_by', table_name='documents')
    op.drop_column('documents', 'trashed_at')
    op.drop_column('documents', 'is_starred')
    op.drop_column('documents', 'doc_type')
    op.drop_column('documents', 'created_by')
