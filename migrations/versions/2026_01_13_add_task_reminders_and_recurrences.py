"""Add task_reminders and task_recurrences tables for reminders and recurring tasks

Revision ID: task_reminders_recurrences
Revises: add_task_assignments_table
Create Date: 2026-01-13 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "task_reminders_recurrences"
down_revision: Union[str, None] = "add_task_assignments_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create task_reminders table
    op.create_table(
        "task_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reminder_type", sa.String(length=50), nullable=False, server_default=sa.text("'in_app'")),
        sa.Column("reminder_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for task_reminders
    op.create_index("ix_task_reminders_task_id", "task_reminders", ["task_id"], unique=False)
    op.create_index("ix_task_reminders_tenant_id", "task_reminders", ["tenant_id"], unique=False)
    op.create_index("ix_task_reminders_reminder_time", "task_reminders", ["reminder_time"], unique=False)
    op.create_index("ix_task_reminders_sent", "task_reminders", ["sent"], unique=False)
    op.create_index("idx_task_reminders_task", "task_reminders", ["task_id", "reminder_time"], unique=False)
    op.create_index("idx_task_reminders_tenant", "task_reminders", ["tenant_id", "reminder_time"], unique=False)
    op.create_index("idx_task_reminders_pending", "task_reminders", ["tenant_id", "sent", "reminder_time"], unique=False)

    # Create task_recurrences table
    op.create_table(
        "task_recurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frequency", sa.String(length=50), nullable=False, server_default=sa.text("'weekly'")),
        sa.Column("interval", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("start_date", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_date", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("max_occurrences", sa.Integer(), nullable=True),
        sa.Column("current_occurrence", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("days_of_week", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("custom_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for task_recurrences
    op.create_index("ix_task_recurrences_task_id", "task_recurrences", ["task_id"], unique=False)
    op.create_index("ix_task_recurrences_tenant_id", "task_recurrences", ["tenant_id"], unique=False)
    op.create_index("ix_task_recurrences_start_date", "task_recurrences", ["start_date"], unique=False)
    op.create_index("ix_task_recurrences_end_date", "task_recurrences", ["end_date"], unique=False)
    op.create_index("ix_task_recurrences_active", "task_recurrences", ["active"], unique=False)
    op.create_index("idx_task_recurrences_task", "task_recurrences", ["task_id", "active"], unique=False)
    op.create_index("idx_task_recurrences_tenant", "task_recurrences", ["tenant_id", "active"], unique=False)
    op.create_index("idx_task_recurrences_dates", "task_recurrences", ["tenant_id", "start_date", "end_date"], unique=False)


def downgrade() -> None:
    # Drop task_recurrences table and indexes
    op.drop_index("idx_task_recurrences_dates", table_name="task_recurrences")
    op.drop_index("idx_task_recurrences_tenant", table_name="task_recurrences")
    op.drop_index("idx_task_recurrences_task", table_name="task_recurrences")
    op.drop_index("ix_task_recurrences_active", table_name="task_recurrences")
    op.drop_index("ix_task_recurrences_end_date", table_name="task_recurrences")
    op.drop_index("ix_task_recurrences_start_date", table_name="task_recurrences")
    op.drop_index("ix_task_recurrences_tenant_id", table_name="task_recurrences")
    op.drop_index("ix_task_recurrences_task_id", table_name="task_recurrences")
    op.drop_table("task_recurrences")

    # Drop task_reminders table and indexes
    op.drop_index("idx_task_reminders_pending", table_name="task_reminders")
    op.drop_index("idx_task_reminders_tenant", table_name="task_reminders")
    op.drop_index("idx_task_reminders_task", table_name="task_reminders")
    op.drop_index("ix_task_reminders_sent", table_name="task_reminders")
    op.drop_index("ix_task_reminders_reminder_time", table_name="task_reminders")
    op.drop_index("ix_task_reminders_tenant_id", table_name="task_reminders")
    op.drop_index("ix_task_reminders_task_id", table_name="task_reminders")
    op.drop_table("task_reminders")
