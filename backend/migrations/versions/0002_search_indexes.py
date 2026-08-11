"""search indexes and generated tsvector

Revision ID: 0002_search_indexes
Revises: 0001_baseline_schema
Create Date: 2026-08-10 17:38:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0002_search_indexes'
down_revision: Union[str, None] = '0001_baseline_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Full-text search column, maintained automatically by Postgres.
    op.execute("""
        ALTER TABLE chunks
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv ON chunks USING GIN (content_tsv)")

    # Approximate-nearest-neighbour index for the vector leg.
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_metadata_value ON metadata USING GIN (value)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_details ON audit_logs USING GIN (details)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_logs_details")
    op.execute("DROP INDEX IF EXISTS idx_metadata_value")
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_tsv")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content_tsv")
