"""add teams tables

Revision ID: 2026_01_16_teams
Revises: add_task_assignments_table
Create Date: 2026-01-16 19:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_01_16_teams'
down_revision: str | None = 'add_task_assignments_table'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_team_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # Columna en BD se llama 'metadata'
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for teams
    op.create_index('idx_teams_tenant', 'teams', ['tenant_id', 'is_active'])
    op.create_index('idx_teams_parent', 'teams', ['tenant_id', 'parent_team_id'])
    op.create_index(op.f('ix_teams_created_at'), 'teams', ['created_at'])
    op.create_index(op.f('ix_teams_is_active'), 'teams', ['is_active'])
    op.create_index(op.f('ix_teams_parent_team_id'), 'teams', ['parent_team_id'])
    op.create_index(op.f('ix_teams_tenant_id'), 'teams', ['tenant_id'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('added_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member')
    )

    # Create indexes for team_members
    op.create_index('idx_team_members_team', 'team_members', ['tenant_id', 'team_id'])
    op.create_index('idx_team_members_user', 'team_members', ['tenant_id', 'user_id'])
    op.create_index(op.f('ix_team_members_team_id'), 'team_members', ['team_id'])
    op.create_index(op.f('ix_team_members_tenant_id'), 'team_members', ['tenant_id'])
    op.create_index(op.f('ix_team_members_user_id'), 'team_members', ['user_id'])

    # Update task_assignments table to add group assignment support
    # Add column assigned_to_group_id if missing, then constraints
    op.add_column(
        'task_assignments',
        sa.Column('assigned_to_group_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add check constraint: at least one must be present
    op.create_check_constraint(
        'check_assignment_target',
        'task_assignments',
        '(assigned_to_id IS NOT NULL) OR (assigned_to_group_id IS NOT NULL)'
    )

    # Add check constraint: only one can be present
    op.create_check_constraint(
        'check_assignment_exclusive',
        'task_assignments',
        '(assigned_to_id IS NULL) OR (assigned_to_group_id IS NULL)'
    )

    # Add index for group assignments
    op.create_index(
        'idx_task_assignments_group',
        'task_assignments',
        ['tenant_id', 'assigned_to_group_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes and constraints from task_assignments
    op.drop_index('idx_task_assignments_group', table_name='task_assignments')
    op.drop_constraint('check_assignment_exclusive', 'task_assignments', type_='check')
    op.drop_constraint('check_assignment_target', 'task_assignments', type_='check')
    op.drop_column('task_assignments', 'assigned_to_group_id')

    # Drop team_members table
    op.drop_index(op.f('ix_team_members_user_id'), table_name='team_members')
    op.drop_index(op.f('ix_team_members_tenant_id'), table_name='team_members')
    op.drop_index(op.f('ix_team_members_team_id'), table_name='team_members')
    op.drop_index('idx_team_members_user', table_name='team_members')
    op.drop_index('idx_team_members_team', table_name='team_members')
    op.drop_table('team_members')

    # Drop teams table
    op.drop_index(op.f('ix_teams_tenant_id'), table_name='teams')
    op.drop_index(op.f('ix_teams_parent_team_id'), table_name='teams')
    op.drop_index(op.f('ix_teams_is_active'), table_name='teams')
    op.drop_index(op.f('ix_teams_created_at'), table_name='teams')
    op.drop_index('idx_teams_parent', table_name='teams')
    op.drop_index('idx_teams_tenant', table_name='teams')
    op.drop_table('teams')
