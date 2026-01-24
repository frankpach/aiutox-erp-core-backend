"""Add task dependencies and resources

Revision ID: 2026_01_23_001
Revises: previous_revision
Create Date: 2026-01-23 10:20:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_23_001'
down_revision = '5ce9e0cd34fc'  # Merge task_assign_audit and task_statuses_templates
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create task_dependencies table
    op.create_table(
        'task_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('depends_on_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dependency_type', sa.String(length=20), nullable=False, server_default='finish_to_start'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depends_on_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'depends_on_id', name='uq_task_dependency')
    )
    op.create_index(op.f('ix_task_dependencies_tenant_id'), 'task_dependencies', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_task_dependencies_task_id'), 'task_dependencies', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_dependencies_depends_on_id'), 'task_dependencies', ['depends_on_id'], unique=False)

    # Create task_resources table
    op.create_table(
        'task_resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(length=20), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocated_hours', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_resources_tenant_id'), 'task_resources', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_task_resources_task_id'), 'task_resources', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_resources_resource_id'), 'task_resources', ['resource_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_resources_resource_id'), table_name='task_resources')
    op.drop_index(op.f('ix_task_resources_task_id'), table_name='task_resources')
    op.drop_index(op.f('ix_task_resources_tenant_id'), table_name='task_resources')
    op.drop_table('task_resources')

    op.drop_index(op.f('ix_task_dependencies_depends_on_id'), table_name='task_dependencies')
    op.drop_index(op.f('ix_task_dependencies_task_id'), table_name='task_dependencies')
    op.drop_index(op.f('ix_task_dependencies_tenant_id'), table_name='task_dependencies')
    op.drop_table('task_dependencies')
