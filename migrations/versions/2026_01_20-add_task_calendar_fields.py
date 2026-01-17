"""Add calendar scheduling fields to tasks

Revision ID: add_task_calendar_fields
Revises: extend_calendar_unified_source
Create Date: 2026-01-20 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_task_calendar_fields"
down_revision: str | None = "extend_calendar_unified_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("start_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("end_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "tasks",
        sa.Column("tag_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("color_override", sa.String(length=7), nullable=True),
    )

    op.create_index("idx_tasks_tenant_start_at", "tasks", ["tenant_id", "start_at"], unique=False)
    op.create_index("idx_tasks_tenant_end_at", "tasks", ["tenant_id", "end_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_tasks_tenant_end_at", table_name="tasks")
    op.drop_index("idx_tasks_tenant_start_at", table_name="tasks")

    op.drop_column("tasks", "color_override")
    op.drop_column("tasks", "tag_ids")
    op.drop_column("tasks", "all_day")
    op.drop_column("tasks", "end_at")
    op.drop_column("tasks", "start_at")
