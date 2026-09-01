"""T66/D-7 bug fix — backfill retention_class for already-trashed documents.

Real bug found 2026-09-01: toggle_trash_document never assigned the
'operational_trash' retention class when a document was trashed, so
cleanup_expired_trashed_items' D-7 class lookup treated every trashed
document as the permanent default class and refused to ever purge it —
the 30-day trash-purge has been silently inert since D-7 shipped, for
every tenant. Fixed going forward in document_service.toggle_trash_document;
this backfills any document that was already sitting in the trash before
that fix landed, so it isn't permanently stuck un-purgeable.

Revision ID: 0044_backfill_retention
Revises: 0043_pdfa_rendition
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0044_backfill_retention'
down_revision: Union[str, None] = '0043_pdfa_rendition'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE doc_dg_documents SET retention_class = 'operational_trash' "
        "WHERE is_trashed = true AND retention_class = 'unclassified_permanent'"
    )


def downgrade() -> None:
    # Not reversible in a targeted way (can't distinguish backfilled rows
    # from ones a human explicitly classified afterward) — no-op.
    pass
