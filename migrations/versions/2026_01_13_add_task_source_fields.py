"""Add source_module, source_id, source_context fields to tasks table

Revision ID: add_task_source_fields
Revises: add_tasks_tables
Create Date: 2026-01-13 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_task_source_fields"
down_revision: str | None = "add_tasks_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add source_module column
    op.add_column(
        "tasks",
        sa.Column("source_module", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_tasks_source_module", "tasks", ["source_module"], unique=False)

    # Add source_id column
    op.add_column(
        "tasks",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tasks_source_id", "tasks", ["source_id"], unique=False)

    # Add source_context column (JSONB)
    op.add_column(
        "tasks",
        sa.Column("source_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Create composite index for source_module and source_id
    op.create_index("idx_tasks_source", "tasks", ["source_module", "source_id"], unique=False)


def downgrade() -> None:
    # Drop composite index
    op.drop_index("idx_tasks_source", table_name="tasks")

    # Drop columns
    op.drop_column("tasks", "source_context")
    op.drop_index("ix_tasks_source_id", table_name="tasks")
    op.drop_column("tasks", "source_id")
    op.drop_index("ix_tasks_source_module", table_name="tasks")
    op.drop_column("tasks", "source_module")
