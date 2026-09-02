"""T50 — add the six persona values to the user_role enum

Split into its own migration: Postgres forbids using a newly-added enum
value in the same transaction that added it, so the values must be
committed here before migration 0022 can UPDATE existing rows onto them.

Revision ID: 0021_persona_roles_enum
Revises: 0020_audit_hash_chain
Create Date: 2026-08-24 00:00:13.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0021_persona_roles_enum'
down_revision: Union[str, None] = '0020_audit_hash_chain'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ROLES = ['records_officer', 'operator', 'department_head', 'legal_counsel', 'it_admin', 'auditor']


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for role in NEW_ROLES:
            op.execute(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{role}'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enum types; the added values are left
    # in place (harmless if unused). Data migrated onto them in 0022 is
    # reverted there, before this migration's downgrade would run.
    pass
