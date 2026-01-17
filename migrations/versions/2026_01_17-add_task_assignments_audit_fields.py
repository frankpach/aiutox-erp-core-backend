"""Add audit fields to task_assignments

Revision ID: 2026_01_17_task_assign_audit
Revises: 2026_01_16_merge_heads
Create Date: 2026-01-17 00:10:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2026_01_17_task_assign_audit"
down_revision: str | None = "2026_01_16_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_assignments",
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "task_assignments",
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.create_index(
        "ix_task_assignments_created_by_id",
        "task_assignments",
        ["created_by_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_task_assignments_created_by_id",
        "task_assignments",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_task_assignments_updated_by_id",
        "task_assignments",
        "users",
        ["updated_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE task_assignments
        SET created_by_id = assigned_by_id
        WHERE created_by_id IS NULL
        """
    )

    op.alter_column(
        "task_assignments",
        "created_by_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "task_assignments",
        "created_by_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.drop_constraint(
        "fk_task_assignments_updated_by_id",
        "task_assignments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_task_assignments_created_by_id",
        "task_assignments",
        type_="foreignkey",
    )
    op.drop_index("ix_task_assignments_created_by_id", table_name="task_assignments")

    op.drop_column("task_assignments", "updated_by_id")
    op.drop_column("task_assignments", "created_by_id")
