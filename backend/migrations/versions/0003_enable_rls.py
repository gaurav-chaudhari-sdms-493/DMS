"""enable row level security

Revision ID: 0003_enable_rls
Revises: 0002_search_indexes
Create Date: 2026-08-10 17:40:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0003_enable_rls'
down_revision: Union[str, None] = '0002_search_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ['documents', 'chunks', 'folders', 'chat_sessions', 'audit_logs', 'api_logs']


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        column = "actor_tenant_id" if table == "audit_logs" else "tenant_id"
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            USING ({column} = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK ({column} = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
