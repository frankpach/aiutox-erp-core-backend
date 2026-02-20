"""add_module_roles_table

Revision ID: 4d08f620a382
Revises: 002_add_business_models
Create Date: 2025-12-09 20:36:02.936062+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4d08f620a382'
down_revision: str | None = '002_add_business_models'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create seeders table (if not exists - this is new)
    op.create_table('seeders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('seeder_name', sa.String(length=255), nullable=False),
    sa.Column('executed_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('seeder_name', name='uq_seeders_name')
    )
    op.create_index(op.f('ix_seeders_seeder_name'), 'seeders', ['seeder_name'], unique=True)

    # Create module_roles table (this is the main purpose of this migration)
    op.create_table('module_roles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('module', sa.String(length=100), nullable=False),
    sa.Column('role_name', sa.String(length=100), nullable=False),
    sa.Column('granted_by', sa.UUID(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'module', 'role_name', name='uq_module_roles_user_module_role')
    )
    op.create_index('idx_module_roles_user_module', 'module_roles', ['user_id', 'module'], unique=False)
    op.create_index(op.f('ix_module_roles_user_id'), 'module_roles', ['user_id'], unique=False)
    # Note: refresh_tokens and user_roles tables were already created in migration 001_add_auth_tables
    # They should not be recreated here. This migration only creates module_roles and seeders.
    # ### end Alembic commands ###


def downgrade() -> None:
    # Drop module_roles table
    op.drop_index(op.f('ix_module_roles_user_id'), table_name='module_roles')
    op.drop_index('idx_module_roles_user_module', table_name='module_roles')
    op.drop_table('module_roles')

    # Drop seeders table
    op.drop_index(op.f('ix_seeders_seeder_name'), table_name='seeders')
    op.drop_table('seeders')

