"""T63 — tamper-evident audit: hash chain columns + append-only trigger

"Make the log append-only in the database itself: the application user
gets no permission to update or delete rows." This deployment runs a
single Postgres role for everything (including migrations), so that
role necessarily owns audit_dg_logs — table ownership bypasses plain
GRANT/REVOKE regardless of what's revoked from it. A BEFORE UPDATE/
DELETE trigger that unconditionally raises is the enforcement that
actually holds here, regardless of which role is connected. A separate,
least-privilege runtime role (REVOKE UPDATE/DELETE from a non-owning
role) is the fuller production answer and remains a follow-up, not
built here.

Revision ID: 0020_audit_hash_chain
Revises: 0019_corpus_calibration
Create Date: 2026-08-24 00:00:12.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0020_audit_hash_chain'
down_revision: Union[str, None] = '0019_corpus_calibration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_dg_logs', sa.Column('previous_hash', sa.Text(), nullable=True))
    op.add_column('audit_dg_logs', sa.Column('event_hash', sa.Text(), nullable=True))
    op.create_index('idx_audit_dg_logs_event_hash', 'audit_dg_logs', ['event_hash'])

    op.execute("""
        CREATE OR REPLACE FUNCTION audit_dg_logs_block_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_dg_logs is append-only: % is not permitted', TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER audit_dg_logs_append_only
        BEFORE UPDATE OR DELETE ON audit_dg_logs
        FOR EACH ROW EXECUTE FUNCTION audit_dg_logs_block_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_dg_logs_append_only ON audit_dg_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_dg_logs_block_mutation()")
    op.drop_index('idx_audit_dg_logs_event_hash', table_name='audit_dg_logs')
    op.drop_column('audit_dg_logs', 'event_hash')
    op.drop_column('audit_dg_logs', 'previous_hash')
