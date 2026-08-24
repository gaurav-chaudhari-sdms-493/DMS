"""T66/D-7 — retention policy engine: data-driven classes, not one global rule

sys_dg_retention_classes is global (not tenant-scoped), same as
doc_dg_templates — a retention class definition doesn't vary per tenant.
Seeded conservatively per D-7: nothing purges by default. doc_dg_documents
and record_dg_records both get a retention_class column defaulting to a
never-purge class, so existing rows are never silently made eligible for
deletion by this migration.

Revision ID: 0024_retention_classes
Revises: 0023_fact_confidence_status
Create Date: 2026-08-24 00:00:12.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0024_retention_classes'
down_revision: Union[str, None] = '0023_fact_confidence_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sys_dg_retention_classes',
        sa.Column('class_name', sa.Text(), primary_key=True),
        sa.Column('retention_days', sa.Integer(), nullable=True),  # NULL = permanent, never purge
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_sys_dg_retention_classes_days_positive',
        'sys_dg_retention_classes',
        'retention_days IS NULL OR retention_days > 0',
    )

    op.bulk_insert(
        sa.table(
            'sys_dg_retention_classes',
            sa.column('class_name', sa.Text()),
            sa.column('retention_days', sa.Integer()),
            sa.column('description', sa.Text()),
        ),
        [
            {
                'class_name': 'unclassified_permanent',
                'retention_days': None,
                'description': 'D-7 default for anything not explicitly classified. Never auto-purged.',
            },
            {
                'class_name': 'operational_trash',
                'retention_days': 30,
                'description': 'User-trashed items. Matches the pre-D-7 30-day trash purge behavior unchanged.',
            },
            {
                'class_name': 'statutory_record',
                'retention_days': None,
                'description': 'Anything tied to a property/entity record (T60/T61). Never engine-purged regardless of age.',
            },
        ],
    )

    op.add_column(
        'doc_dg_documents',
        sa.Column('retention_class', sa.Text(), nullable=False, server_default='unclassified_permanent'),
    )
    op.create_foreign_key(
        'fk_doc_dg_documents_retention_class', 'doc_dg_documents', 'sys_dg_retention_classes',
        ['retention_class'], ['class_name'],
    )

    op.add_column(
        'record_dg_records',
        sa.Column('retention_class', sa.Text(), nullable=False, server_default='statutory_record'),
    )
    op.create_foreign_key(
        'fk_record_dg_records_retention_class', 'record_dg_records', 'sys_dg_retention_classes',
        ['retention_class'], ['class_name'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_record_dg_records_retention_class', 'record_dg_records', type_='foreignkey')
    op.drop_column('record_dg_records', 'retention_class')
    op.drop_constraint('fk_doc_dg_documents_retention_class', 'doc_dg_documents', type_='foreignkey')
    op.drop_column('doc_dg_documents', 'retention_class')
    op.drop_table('sys_dg_retention_classes')
