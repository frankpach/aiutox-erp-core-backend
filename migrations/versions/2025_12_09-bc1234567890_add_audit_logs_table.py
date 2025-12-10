"""Add audit_logs table

Revision ID: 57d4493a7380
Revises: af20de189f20
Create Date: 2025-12-09 22:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '57d4493a7380'
down_revision: Union[str, None] = 'af20de189f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='User who performed the action (null for system actions)'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Tenant ID for multi-tenancy isolation'),
        sa.Column('action', sa.String(length=100), nullable=False, comment="Action type (e.g., 'grant_permission', 'create_user')"),
        sa.Column('resource_type', sa.String(length=50), nullable=True, comment="Type of resource affected (e.g., 'user', 'permission', 'role')"),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True, comment='ID of the resource affected'),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional details as JSON'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='Client IP address (supports IPv6)'),
        sa.Column('user_agent', sa.String(length=500), nullable=True, comment='Client user agent string'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)

    # Composite indexes for common queries
    op.create_index('idx_audit_logs_tenant_created', 'audit_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_audit_logs_action_created', 'audit_logs', ['action', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_audit_logs_action_created', table_name='audit_logs')
    op.drop_index('idx_audit_logs_tenant_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_tenant_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')

    # Drop table
    op.drop_table('audit_logs')

