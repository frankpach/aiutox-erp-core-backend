"""Add system_configs table

Revision ID: a8ae578ac76b
Revises: 57d4493a7380
Create Date: 2025-12-11 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a8ae578ac76b'
down_revision: Union[str, None] = '57d4493a7380'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_configs table
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, comment='Tenant ID for multi-tenancy isolation'),
        sa.Column('module', sa.String(length=100), nullable=False, comment="Module name (e.g., 'products', 'inventory')"),
        sa.Column('key', sa.String(length=255), nullable=False, comment='Configuration key'),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Configuration value (JSON)'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'module', 'key', name='uq_system_configs_tenant_module_key')
    )

    # Create indexes for efficient queries
    op.create_index('ix_system_configs_tenant_id', 'system_configs', ['tenant_id'], unique=False)
    op.create_index('ix_system_configs_module', 'system_configs', ['module'], unique=False)

    # Composite index for common queries
    op.create_index('idx_system_configs_tenant_module', 'system_configs', ['tenant_id', 'module'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_system_configs_tenant_module', table_name='system_configs')
    op.drop_index('ix_system_configs_module', table_name='system_configs')
    op.drop_index('ix_system_configs_tenant_id', table_name='system_configs')

    # Drop table
    op.drop_table('system_configs')
