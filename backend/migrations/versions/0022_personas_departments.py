"""T50 — migrate existing users onto the new personas + department groups

"Department scope is an RBAC group over projects, not a container
level" — a department is a named group of users granted scope over a
set of folders (projects), independent of folder nesting depth.

Revision ID: 0022_persona_migration_and_departments
Revises: 0021_persona_roles_enum
Create Date: 2026-08-24 00:00:14.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0022_personas_departments'
down_revision: Union[str, None] = '0021_persona_roles_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ['iam_dg_departments', 'iam_dg_department_members', 'iam_dg_department_folders']


def upgrade() -> None:
    # Existing binary roles map onto the closest new persona rather than
    # staying on the old values: 'admin' (system-level access) -> 'it_admin'
    # (tenant-wide, unrestricted, matches current behaviour exactly);
    # 'user' (the only other role, day-to-day usage) -> 'operator'.
    op.execute("UPDATE iam_dg_users SET role = 'it_admin' WHERE role = 'admin'")
    op.execute("UPDATE iam_dg_users SET role = 'operator' WHERE role = 'user'")

    op.create_table(
        'iam_dg_departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_by_actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_foreign_key('fk_iam_dg_departments_tenant', 'iam_dg_departments', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_iam_dg_departments_actor', 'iam_dg_departments', 'iam_dg_users', ['created_by_actor_id'], ['id'])
    op.create_index('idx_iam_dg_departments_tenant_id', 'iam_dg_departments', ['tenant_id'])

    op.create_table(
        'iam_dg_department_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('department_id', 'user_id', name='uq_iam_dg_department_members'),
    )
    op.create_foreign_key('fk_iam_dg_department_members_tenant', 'iam_dg_department_members', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_iam_dg_department_members_department', 'iam_dg_department_members', 'iam_dg_departments', ['department_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_iam_dg_department_members_user', 'iam_dg_department_members', 'iam_dg_users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_iam_dg_department_members_tenant_id', 'iam_dg_department_members', ['tenant_id'])
    op.create_index('idx_iam_dg_department_members_department_id', 'iam_dg_department_members', ['department_id'])
    op.create_index('idx_iam_dg_department_members_user_id', 'iam_dg_department_members', ['user_id'])

    op.create_table(
        'iam_dg_department_folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('folder_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('department_id', 'folder_id', name='uq_iam_dg_department_folders'),
    )
    op.create_foreign_key('fk_iam_dg_department_folders_tenant', 'iam_dg_department_folders', 'iam_dg_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_iam_dg_department_folders_department', 'iam_dg_department_folders', 'iam_dg_departments', ['department_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_iam_dg_department_folders_folder', 'iam_dg_department_folders', 'doc_dg_folders', ['folder_id'], ['id'], ondelete='CASCADE')
    op.create_index('idx_iam_dg_department_folders_tenant_id', 'iam_dg_department_folders', ['tenant_id'])
    op.create_index('idx_iam_dg_department_folders_department_id', 'iam_dg_department_folders', ['department_id'])
    op.create_index('idx_iam_dg_department_folders_folder_id', 'iam_dg_department_folders', ['folder_id'])

    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table('iam_dg_department_folders')
    op.drop_table('iam_dg_department_members')
    op.drop_table('iam_dg_departments')

    op.execute("UPDATE iam_dg_users SET role = 'admin' WHERE role = 'it_admin'")
    op.execute("UPDATE iam_dg_users SET role = 'user' WHERE role = 'operator'")
