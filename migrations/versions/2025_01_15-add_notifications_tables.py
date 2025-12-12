"""Add notifications tables: notification_templates, notification_queue

Revision ID: add_notifications_tables
Revises: add_reporting_tables
Create Date: 2025-01-15 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_notifications_tables"
down_revision: Union[str, None] = "add_reporting_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_templates table
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_templates_tenant_id", "notification_templates", ["tenant_id"], unique=False)
    op.create_index("ix_notification_templates_event_type", "notification_templates", ["event_type"], unique=False)
    op.create_index("idx_notification_templates_tenant_event", "notification_templates", ["tenant_id", "event_type"], unique=False)
    op.create_index("idx_notification_templates_event_channel", "notification_templates", ["event_type", "channel"], unique=False)

    # Create notification_queue table
    op.create_table(
        "notification_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["notification_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_queue_event_type", "notification_queue", ["event_type"], unique=False)
    op.create_index("ix_notification_queue_recipient_id", "notification_queue", ["recipient_id"], unique=False)
    op.create_index("ix_notification_queue_tenant_id", "notification_queue", ["tenant_id"], unique=False)
    op.create_index("ix_notification_queue_channel", "notification_queue", ["channel"], unique=False)
    op.create_index("ix_notification_queue_template_id", "notification_queue", ["template_id"], unique=False)
    op.create_index("ix_notification_queue_status", "notification_queue", ["status"], unique=False)
    op.create_index("ix_notification_queue_created_at", "notification_queue", ["created_at"], unique=False)
    op.create_index("idx_notification_queue_status", "notification_queue", ["status"], unique=False)
    op.create_index("idx_notification_queue_created", "notification_queue", ["created_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_notification_queue_created", table_name="notification_queue")
    op.drop_index("idx_notification_queue_status", table_name="notification_queue")
    op.drop_index("ix_notification_queue_created_at", table_name="notification_queue")
    op.drop_index("ix_notification_queue_status", table_name="notification_queue")
    op.drop_index("ix_notification_queue_template_id", table_name="notification_queue")
    op.drop_index("ix_notification_queue_channel", table_name="notification_queue")
    op.drop_index("ix_notification_queue_tenant_id", table_name="notification_queue")
    op.drop_index("ix_notification_queue_recipient_id", table_name="notification_queue")
    op.drop_index("ix_notification_queue_event_type", table_name="notification_queue")
    op.drop_index("idx_notification_templates_event_channel", table_name="notification_templates")
    op.drop_index("idx_notification_templates_tenant_event", table_name="notification_templates")
    op.drop_index("ix_notification_templates_event_type", table_name="notification_templates")
    op.drop_index("ix_notification_templates_tenant_id", table_name="notification_templates")

    # Drop tables
    op.drop_table("notification_queue")
    op.drop_table("notification_templates")


