"""Add task_assignments table

Revision ID: add_task_assignments_table
Revises: add_task_source_fields
Create Date: 2026-01-13 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_task_assignments_table"
down_revision: Union[str, None] = "add_task_source_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create task_assignments table
    op.create_table(
        "task_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_task_assignments_task_id", "task_assignments", ["task_id"], unique=False)
    op.create_index("ix_task_assignments_tenant_id", "task_assignments", ["tenant_id"], unique=False)
    op.create_index("ix_task_assignments_assigned_to_id", "task_assignments", ["assigned_to_id"], unique=False)
    op.create_index("ix_task_assignments_assigned_at", "task_assignments", ["assigned_at"], unique=False)

    # Create composite indexes
    op.create_index("idx_task_assignments_task", "task_assignments", ["task_id", "assigned_at"], unique=False)
    op.create_index("idx_task_assignments_user", "task_assignments", ["tenant_id", "assigned_to_id"], unique=False)


def downgrade() -> None:
    # Drop composite indexes
    op.drop_index("idx_task_assignments_user", table_name="task_assignments")
    op.drop_index("idx_task_assignments_task", table_name="task_assignments")

    # Drop indexes
    op.drop_index("ix_task_assignments_assigned_at", table_name="task_assignments")
    op.drop_index("ix_task_assignments_assigned_to_id", table_name="task_assignments")
    op.drop_index("ix_task_assignments_tenant_id", table_name="task_assignments")
    op.drop_index("ix_task_assignments_task_id", table_name="task_assignments")

    # Drop table
    op.drop_table("task_assignments")
