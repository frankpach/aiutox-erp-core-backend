"""Add task_statuses and task_templates tables for customizable statuses and task templates

Revision ID: add_task_statuses_templates
Revises: add_task_calendar_fields
Create Date: 2026-01-20 10:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_task_statuses_templates"
down_revision: str | None = "add_task_calendar_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create task_statuses table
    op.create_table(
        "task_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_statuses_tenant_id", "task_statuses", ["tenant_id"], unique=False)
    op.create_index("idx_task_statuses_tenant_order", "task_statuses", ["tenant_id", "order"], unique=False)
    op.create_index("idx_task_statuses_tenant_type", "task_statuses", ["tenant_id", "type"], unique=False)

    # Create task_templates table
    op.create_table(
        "task_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_hours", sa.Integer(), nullable=True),
        sa.Column("default_status_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_status_id"], ["task_statuses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_templates_tenant_id", "task_templates", ["tenant_id"], unique=False)
    op.create_index("idx_task_templates_tenant_name", "task_templates", ["tenant_id", "name"], unique=False)

    # Add columns to tasks table for Board view and templates
    op.add_column("tasks", sa.Column("status_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("board_order", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Create foreign keys
    op.create_foreign_key(
        "fk_tasks_status_id",
        "tasks",
        "task_statuses",
        ["status_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_tasks_template_id",
        "tasks",
        "task_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL"
    )

    # Create indices for tasks
    op.create_index("idx_tasks_status_id", "tasks", ["status_id"], unique=False)
    op.create_index("idx_tasks_board_order", "tasks", ["status_id", "board_order"], unique=False)
    op.create_index("idx_tasks_template_id", "tasks", ["template_id"], unique=False)

    # Insert default task statuses for all existing tenants
    op.execute("""
        INSERT INTO task_statuses (id, tenant_id, name, type, color, is_system, "order")
        SELECT
            gen_random_uuid(),
            t.id,
            s.name,
            s.type,
            s.color,
            true,
            s."order"
        FROM tenants t
        CROSS JOIN (VALUES
            ('Por Iniciar', 'open', '#2196F3', 1),
            ('En Proceso', 'in_progress', '#FF9800', 2),
            ('Pausado', 'in_progress', '#FFC107', 3),
            ('Cancelado', 'closed', '#F44336', 4),
            ('Completado', 'closed', '#4CAF50', 5)
        ) AS s(name, type, color, "order")
    """)

    # Migrate existing tasks to use status_id
    op.execute("""
        UPDATE tasks
        SET status_id = (
            SELECT id FROM task_statuses
            WHERE tenant_id = tasks.tenant_id
            AND name = CASE
                WHEN tasks.status = 'todo' THEN 'Por Iniciar'
                WHEN tasks.status = 'in_progress' THEN 'En Proceso'
                WHEN tasks.status = 'done' THEN 'Completado'
                WHEN tasks.status = 'cancelled' THEN 'Cancelado'
                ELSE 'Por Iniciar'
            END
            LIMIT 1
        )
    """)

    # Update board_order separately using window function
    op.execute("""
        WITH numbered_tasks AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY tenant_id, status
                       ORDER BY created_at
                   ) as rn
            FROM tasks
        )
        UPDATE tasks
        SET board_order = numbered_tasks.rn
        FROM numbered_tasks
        WHERE tasks.id = numbered_tasks.id
    """)


def downgrade() -> None:
    # Drop indices
    op.drop_index("idx_tasks_template_id", table_name="tasks")
    op.drop_index("idx_tasks_board_order", table_name="tasks")
    op.drop_index("idx_tasks_status_id", table_name="tasks")

    # Drop foreign keys
    op.drop_constraint("fk_tasks_template_id", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_status_id", "tasks", type_="foreignkey")

    # Drop columns from tasks
    op.drop_column("tasks", "template_id")
    op.drop_column("tasks", "board_order")
    op.drop_column("tasks", "status_id")

    # Drop tables
    op.drop_table("task_templates")
    op.drop_table("task_statuses")
