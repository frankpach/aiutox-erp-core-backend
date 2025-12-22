"""Add config_versions table

Revision ID: 2025_12_21_config_versions
Revises: 2025_12_11-a8ae578ac76b
Create Date: 2025-12-21 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2025_12_21_config_versions'
down_revision: Union[str, None] = '2025_12_11-a8ae578ac76b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create config_versions table
    op.create_table(
        'config_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('system_configs.id', ondelete='CASCADE'), nullable=False, comment='Reference to the configuration entry'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Tenant ID for multi-tenancy isolation'),
        sa.Column('module', sa.String(length=100), nullable=False, comment="Module name (e.g., 'products', 'inventory', 'app_theme')"),
        sa.Column('key', sa.String(length=200), nullable=False, comment='Configuration key within the module'),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Configuration value (stored as JSON for flexibility)'),
        sa.Column('version_number', sa.Integer(), nullable=False, comment='Sequential version number for this config key'),
        sa.Column('change_type', sa.String(length=20), nullable=False, comment="Type of change: 'create', 'update', 'delete'"),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='User who made the change (null for system changes)'),
        sa.Column('change_reason', sa.Text(), nullable=True, comment='Optional reason for the change'),
        sa.Column('change_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional metadata (IP, user agent, etc.)'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'), comment='Timestamp when this version was created'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_config_versions_config_id', 'config_versions', ['config_id'], unique=False)
    op.create_index('ix_config_versions_tenant_id', 'config_versions', ['tenant_id'], unique=False)
    op.create_index('ix_config_versions_module', 'config_versions', ['module'], unique=False)
    op.create_index('ix_config_versions_key', 'config_versions', ['key'], unique=False)
    op.create_index('ix_config_versions_created_at', 'config_versions', ['created_at'], unique=False)

    # Composite indexes
    op.create_index('ix_config_versions_tenant_module', 'config_versions', ['tenant_id', 'module'], unique=False)
    op.create_index('ix_config_versions_config_version', 'config_versions', ['config_id', 'version_number'], unique=False)
    op.create_index('ix_config_versions_tenant_module_key', 'config_versions', ['tenant_id', 'module', 'key'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_config_versions_tenant_module_key', table_name='config_versions')
    op.drop_index('ix_config_versions_config_version', table_name='config_versions')
    op.drop_index('ix_config_versions_tenant_module', table_name='config_versions')
    op.drop_index('ix_config_versions_created_at', table_name='config_versions')
    op.drop_index('ix_config_versions_key', table_name='config_versions')
    op.drop_index('ix_config_versions_module', table_name='config_versions')
    op.drop_index('ix_config_versions_tenant_id', table_name='config_versions')
    op.drop_index('ix_config_versions_config_id', table_name='config_versions')

    # Drop table
    op.drop_table('config_versions')

