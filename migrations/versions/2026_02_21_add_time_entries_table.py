"""add_time_entries_table

Add time_entries table for task time tracking.

Revision ID: 2026_02_21_time_entries
Revises: dd4439c2fee5
Create Date: 2026-02-21 06:00:00.000000+00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2026_02_21_time_entries"
down_revision: str | None = "dd4439c2fee5"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("entry_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_time_entries_task", "time_entries", ["tenant_id", "task_id"])
    op.create_index("idx_time_entries_user", "time_entries", ["tenant_id", "user_id"])
    op.create_index(
        "idx_time_entries_active",
        "time_entries",
        ["tenant_id", "user_id", "end_time"],
    )


def downgrade() -> None:
    op.drop_index("idx_time_entries_active", table_name="time_entries")
    op.drop_index("idx_time_entries_user", table_name="time_entries")
    op.drop_index("idx_time_entries_task", table_name="time_entries")
    op.drop_table("time_entries")
