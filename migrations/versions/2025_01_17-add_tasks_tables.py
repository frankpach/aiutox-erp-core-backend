"""Add tasks tables: tasks, task_checklist_items, workflows, workflow_steps, workflow_executions

Revision ID: add_tasks_tables
Revises: add_files_tables
Create Date: 2025-01-17 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_tasks_tables"
down_revision: Union[str, None] = "add_files_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workflows table first (tasks reference it)
    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"], unique=False)
    op.create_index("ix_workflows_enabled", "workflows", ["enabled"], unique=False)
    op.create_index("idx_workflows_tenant_enabled", "workflows", ["tenant_id", "enabled"], unique=False)

    # Create workflow_steps table
    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("step_type", sa.String(length=50), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transitions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_steps_workflow_id", "workflow_steps", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_steps_tenant_id", "workflow_steps", ["tenant_id"], unique=False)
    op.create_index("idx_workflow_steps_workflow", "workflow_steps", ["workflow_id", "order"], unique=False)

    # Create workflow_executions table
    op.create_table(
        "workflow_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("current_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_step_id"], ["workflow_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_executions_workflow_id", "workflow_executions", ["workflow_id"], unique=False)
    op.create_index("ix_workflow_executions_tenant_id", "workflow_executions", ["tenant_id"], unique=False)
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"], unique=False)
    op.create_index("ix_workflow_executions_entity_type", "workflow_executions", ["entity_type"], unique=False)
    op.create_index("ix_workflow_executions_entity_id", "workflow_executions", ["entity_id"], unique=False)
    op.create_index("ix_workflow_executions_started_at", "workflow_executions", ["started_at"], unique=False)
    op.create_index("idx_workflow_executions_workflow", "workflow_executions", ["workflow_id", "status"], unique=False)
    op.create_index("idx_workflow_executions_entity", "workflow_executions", ["entity_type", "entity_id"], unique=False)

    # Create tasks table (after workflows and workflow_steps)
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_date", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_step_id"], ["workflow_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], unique=False)
    op.create_index("ix_tasks_assigned_to_id", "tasks", ["assigned_to_id"], unique=False)
    op.create_index("ix_tasks_created_by_id", "tasks", ["created_by_id"], unique=False)
    op.create_index("ix_tasks_related_entity_type", "tasks", ["related_entity_type"], unique=False)
    op.create_index("ix_tasks_related_entity_id", "tasks", ["related_entity_id"], unique=False)
    op.create_index("ix_tasks_workflow_id", "tasks", ["workflow_id"], unique=False)
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"], unique=False)
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"], unique=False)
    op.create_index("idx_tasks_tenant_status", "tasks", ["tenant_id", "status"], unique=False)
    op.create_index("idx_tasks_tenant_priority", "tasks", ["tenant_id", "priority"], unique=False)
    op.create_index("idx_tasks_assigned", "tasks", ["tenant_id", "assigned_to_id"], unique=False)
    op.create_index("idx_tasks_due_date", "tasks", ["tenant_id", "due_date"], unique=False)
    op.create_index("idx_tasks_entity", "tasks", ["related_entity_type", "related_entity_id"], unique=False)

    # Create task_checklist_items table
    op.create_table(
        "task_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"], unique=False)
    op.create_index("ix_task_checklist_items_tenant_id", "task_checklist_items", ["tenant_id"], unique=False)
    op.create_index("ix_task_checklist_items_completed", "task_checklist_items", ["completed"], unique=False)
    op.create_index("idx_task_checklist_task", "task_checklist_items", ["task_id", "order"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_workflow_executions_entity", table_name="workflow_executions")
    op.drop_index("idx_workflow_executions_workflow", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_started_at", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_entity_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_entity_type", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_tenant_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_id", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("idx_workflow_steps_workflow", table_name="workflow_steps")
    op.drop_index("ix_workflow_steps_tenant_id", table_name="workflow_steps")
    op.drop_index("ix_workflow_steps_workflow_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_index("idx_task_checklist_task", table_name="task_checklist_items")
    op.drop_index("ix_task_checklist_items_completed", table_name="task_checklist_items")
    op.drop_index("ix_task_checklist_items_tenant_id", table_name="task_checklist_items")
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")

    op.drop_index("idx_tasks_entity", table_name="tasks")
    op.drop_index("idx_tasks_due_date", table_name="tasks")
    op.drop_index("idx_tasks_assigned", table_name="tasks")
    op.drop_index("idx_tasks_tenant_priority", table_name="tasks")
    op.drop_index("idx_tasks_tenant_status", table_name="tasks")
    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    op.drop_index("ix_tasks_workflow_id", table_name="tasks")
    op.drop_index("ix_tasks_related_entity_id", table_name="tasks")
    op.drop_index("ix_tasks_related_entity_type", table_name="tasks")
    op.drop_index("ix_tasks_created_by_id", table_name="tasks")
    op.drop_index("ix_tasks_assigned_to_id", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_tenant_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("idx_workflows_tenant_enabled", table_name="workflows")
    op.drop_index("ix_workflows_enabled", table_name="workflows")
    op.drop_index("ix_workflows_tenant_id", table_name="workflows")
    op.drop_table("workflows")

