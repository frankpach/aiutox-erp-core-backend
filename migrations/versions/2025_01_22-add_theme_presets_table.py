"""Add theme_presets table

Revision ID: 2025_01_22_theme_presets
Revises: 2025_12_21_config_versions
Create Date: 2025-01-22 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2025_01_22_theme_presets'
down_revision: Union[str, None] = '2025_12_21_config_versions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create theme_presets table
    op.create_table(
        'theme_presets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, comment='Tenant ID for multi-tenancy isolation'),
        sa.Column('name', sa.String(length=255), nullable=False, comment="Preset name (e.g., 'Original', 'Dark Mode')"),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional description of the preset'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Theme configuration dictionary (colors, logos, fonts, etc.)'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Whether this is the default preset for the tenant'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Whether this is a system preset (cannot be deleted or edited)'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment='User who created this preset (NULL for system presets)'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_theme_presets_tenant_id', 'theme_presets', ['tenant_id'], unique=False)

    # Composite indexes
    op.create_index('idx_theme_presets_system', 'theme_presets', ['is_system', 'name'], unique=False)
    op.create_index('idx_theme_presets_tenant', 'theme_presets', ['tenant_id', 'is_default'], unique=False)

    # Partial unique index: Only one default preset per tenant (when is_default is True)
    op.execute("""
        CREATE UNIQUE INDEX uq_theme_presets_tenant_default
        ON theme_presets (tenant_id)
        WHERE is_default = true
    """)


def downgrade() -> None:
    # Drop indexes (including partial unique index)
    op.execute("DROP INDEX IF EXISTS uq_theme_presets_tenant_default")
    op.drop_index('idx_theme_presets_tenant', table_name='theme_presets')
    op.drop_index('idx_theme_presets_system', table_name='theme_presets')
    op.drop_index('ix_theme_presets_tenant_id', table_name='theme_presets')

    # Drop table
    op.drop_table('theme_presets')

