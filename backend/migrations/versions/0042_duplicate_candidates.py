"""T79 — doc_dg_documents.possible_duplicate_candidates.

Fuzzy-duplicate detection (duplicate_service.find_fuzzy_duplicates,
embedding-cosine-similarity on the first chunk) existed but was only
reachable on-demand via GET /{document_id}/fuzzy-duplicates — never run
during ingestion, so an operator would only see it if they thought to
ask. This wires it into the ingest path as an informational, non-blocking
signal, same convention as TS2's data_loss_details and TS6's
page_furniture_candidates: NULL for the common case (nothing found),
surfaced for operator resolution, never auto-merged or blocked.

Revision ID: 0042_duplicate_candidates
Revises: 0041_remaining_thresholds
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '0042_duplicate_candidates'
down_revision: Union[str, None] = '0041_remaining_thresholds'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doc_dg_documents', sa.Column('possible_duplicate_candidates', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('doc_dg_documents', 'possible_duplicate_candidates')
