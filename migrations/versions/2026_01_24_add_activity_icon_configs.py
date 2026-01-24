"""Add activity icon configs

Revision ID: add_activity_icon_configs
Revises:
Create Date: 2026-01-24

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_24_001'
down_revision = '2026_01_23_002'
branch_labels = None
depends_on = None


def upgrade():
    """Create activity_icon_configs table"""
    op.create_table(
        'activity_icon_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=False),
        sa.Column('class_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        'idx_tenant_activity_status',
        'activity_icon_configs',
        ['tenant_id', 'activity_type', 'status'],
        unique=True
    )
    op.create_index(
        op.f('ix_activity_icon_configs_tenant_id'),
        'activity_icon_configs',
        ['tenant_id'],
        unique=False
    )


def downgrade():
    """Drop activity_icon_configs table"""
    op.drop_index(op.f('ix_activity_icon_configs_tenant_id'), table_name='activity_icon_configs')
    op.drop_index('idx_tenant_activity_status', table_name='activity_icon_configs')
    op.drop_table('activity_icon_configs')
