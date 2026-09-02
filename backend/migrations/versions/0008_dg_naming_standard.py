"""rename all tables, FKs, unique constraints and indexes to the {module}_dg_* standard

T01 — engineering standard from Build Design v0.3 Section 12 / Scope Gap Section 6.
Renames only. No column, type or data changes. Row-level security policies stay
attached automatically (Postgres ties policies to the table OID, not its name),
so 0003_enable_rls's tenant_isolation_policy needs no action here.

Revision ID: 0008_dg_naming_standard
Revises: 0007_chat_created_at_default
Create Date: 2026-08-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = '0008_dg_naming_standard'
down_revision: Union[str, None] = '0007_chat_created_at_default'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# old table name -> new table name
TABLE_RENAMES = [
    ('tenants', 'iam_dg_tenants'),
    ('users', 'iam_dg_users'),
    ('permissions', 'iam_dg_permissions'),
    ('folders', 'doc_dg_folders'),
    ('documents', 'doc_dg_documents'),
    ('document_versions', 'doc_dg_document_versions'),
    ('chunks', 'doc_dg_chunks'),
    ('metadata', 'doc_dg_metadata_items'),
    ('chat_sessions', 'chat_dg_sessions'),
    ('chat_messages', 'chat_dg_messages'),
    ('audit_logs', 'audit_dg_logs'),
    ('api_logs', 'audit_dg_api_logs'),
]

# (new table name, old constraint name, new constraint name) for foreign keys
FK_RENAMES = [
    ('iam_dg_users', 'users_tenant_id_fkey', 'fk_iam_dg_users_tenant'),
    ('doc_dg_folders', 'folders_parent_id_fkey', 'fk_doc_dg_folders_parent'),
    ('doc_dg_folders', 'folders_tenant_id_fkey', 'fk_doc_dg_folders_tenant'),
    ('doc_dg_folders', 'folders_created_by_fkey', 'fk_doc_dg_folders_created_by'),
    ('doc_dg_documents', 'documents_folder_id_fkey', 'fk_doc_dg_documents_folder'),
    ('doc_dg_documents', 'fk_documents_current_version_id', 'fk_doc_dg_documents_current_version'),
    ('doc_dg_documents', 'documents_created_by_fkey', 'fk_doc_dg_documents_created_by'),
    ('doc_dg_documents', 'documents_tenant_id_fkey', 'fk_doc_dg_documents_tenant'),
    ('doc_dg_document_versions', 'document_versions_uploaded_by_fkey', 'fk_doc_dg_document_versions_uploaded_by'),
    ('doc_dg_document_versions', 'document_versions_document_id_fkey', 'fk_doc_dg_document_versions_document'),
    ('doc_dg_chunks', 'chunks_version_id_fkey', 'fk_doc_dg_chunks_version'),
    ('doc_dg_chunks', 'chunks_tenant_id_fkey', 'fk_doc_dg_chunks_tenant'),
    ('doc_dg_chunks', 'chunks_document_id_fkey', 'fk_doc_dg_chunks_document'),
    ('doc_dg_metadata_items', 'metadata_document_id_fkey', 'fk_doc_dg_metadata_items_document'),
    ('iam_dg_permissions', 'permissions_user_id_fkey', 'fk_iam_dg_permissions_user'),
    ('audit_dg_logs', 'audit_logs_actor_tenant_id_fkey', 'fk_audit_dg_logs_actor_tenant'),
    ('audit_dg_logs', 'audit_logs_actor_user_id_fkey', 'fk_audit_dg_logs_actor'),
    ('chat_dg_sessions', 'chat_sessions_user_id_fkey', 'fk_chat_dg_sessions_user'),
    ('chat_dg_sessions', 'chat_sessions_tenant_id_fkey', 'fk_chat_dg_sessions_tenant'),
    ('chat_dg_messages', 'chat_messages_session_id_fkey', 'fk_chat_dg_messages_session'),
    ('audit_dg_api_logs', 'api_logs_tenant_id_fkey', 'fk_audit_dg_api_logs_tenant'),
    ('audit_dg_api_logs', 'api_logs_user_id_fkey', 'fk_audit_dg_api_logs_user'),
]

# (new table name, old constraint name, new constraint name) for the one unique constraint
UNIQUE_RENAMES = [
    ('iam_dg_users', 'uq_users_email', 'uq_iam_dg_users_email'),
]

# (new table name, old index name, new index name)
INDEX_RENAMES = [
    ('iam_dg_tenants', 'ix_tenants_name', 'idx_iam_dg_tenants_name'),
    ('iam_dg_users', 'ix_users_tenant_id', 'idx_iam_dg_users_tenant_id'),
    ('iam_dg_users', 'ix_users_email', 'idx_iam_dg_users_email'),
    ('doc_dg_folders', 'ix_folders_tenant_id', 'idx_doc_dg_folders_tenant_id'),
    ('doc_dg_folders', 'ix_folders_parent_id', 'idx_doc_dg_folders_parent_id'),
    ('doc_dg_folders', 'ix_folders_created_by', 'idx_doc_dg_folders_created_by'),
    ('doc_dg_documents', 'ix_documents_tenant_id', 'idx_doc_dg_documents_tenant_id'),
    ('doc_dg_documents', 'ix_documents_folder_id', 'idx_doc_dg_documents_folder_id'),
    ('doc_dg_documents', 'ix_documents_created_by', 'idx_doc_dg_documents_created_by'),
    ('doc_dg_document_versions', 'ix_document_versions_document_id', 'idx_doc_dg_document_versions_document_id'),
    ('doc_dg_document_versions', 'ix_document_versions_uploaded_by', 'idx_doc_dg_document_versions_uploaded_by'),
    ('doc_dg_chunks', 'ix_chunks_document_id', 'idx_doc_dg_chunks_document_id'),
    ('doc_dg_chunks', 'ix_chunks_version_id', 'idx_doc_dg_chunks_version_id'),
    ('doc_dg_chunks', 'ix_chunks_tenant_id', 'idx_doc_dg_chunks_tenant_id'),
    ('doc_dg_chunks', 'idx_chunks_content_tsv', 'idx_doc_dg_chunks_content_tsv'),
    ('doc_dg_chunks', 'idx_chunks_embedding', 'idx_doc_dg_chunks_embedding'),
    ('doc_dg_metadata_items', 'ix_metadata_document_id', 'idx_doc_dg_metadata_items_document_id'),
    ('doc_dg_metadata_items', 'idx_metadata_value', 'idx_doc_dg_metadata_items_value'),
    ('iam_dg_permissions', 'ix_permissions_user_id', 'idx_iam_dg_permissions_user_id'),
    ('audit_dg_logs', 'ix_audit_logs_actor_id', 'idx_audit_dg_logs_actor_id'),
    ('audit_dg_logs', 'ix_audit_logs_actor_tenant_id', 'idx_audit_dg_logs_actor_tenant_id'),
    ('audit_dg_logs', 'idx_audit_logs_details', 'idx_audit_dg_logs_details'),
    ('chat_dg_sessions', 'ix_chat_sessions_tenant_id', 'idx_chat_dg_sessions_tenant_id'),
    ('chat_dg_sessions', 'ix_chat_sessions_user_id', 'idx_chat_dg_sessions_user_id'),
    ('chat_dg_messages', 'ix_chat_messages_session_id', 'idx_chat_dg_messages_session_id'),
    ('audit_dg_api_logs', 'ix_api_logs_tenant_id', 'idx_audit_dg_api_logs_tenant_id'),
    ('audit_dg_api_logs', 'ix_api_logs_user_id', 'idx_audit_dg_api_logs_user_id'),
]


def upgrade() -> None:
    for old, new in TABLE_RENAMES:
        op.execute(f'ALTER TABLE {old} RENAME TO {new}')

    for table, old, new in FK_RENAMES:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}')

    for table, old, new in UNIQUE_RENAMES:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}')

    for table, old, new in INDEX_RENAMES:
        op.execute(f'ALTER INDEX {old} RENAME TO {new}')


def downgrade() -> None:
    for table, old, new in INDEX_RENAMES:
        op.execute(f'ALTER INDEX {new} RENAME TO {old}')

    for table, old, new in UNIQUE_RENAMES:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}')

    for table, old, new in FK_RENAMES:
        op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}')

    for old, new in TABLE_RENAMES:
        op.execute(f'ALTER TABLE {new} RENAME TO {old}')
