"""Initial migration

Revision ID: b7a5e3c4e3b0
Revises: 
Create Date: 2024-07-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'b7a5e3c4e3b0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('doc_type', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    )
    op.create_index(op.f('ix_documents_tenant_id'), 'documents', ['tenant_id'], unique=False)

    op.create_table(
        'chunks',
        sa.Column('chunk_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.TEXT(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('chunk_metadata', sa.JSONB(), nullable=False),
        sa.Column('page_number', sa.INTEGER(), nullable=True),
        sa.Column('s3_path', sa.TEXT(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_chunks_tenant_id'), 'chunks', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('chunks')
    op.drop_table('documents')