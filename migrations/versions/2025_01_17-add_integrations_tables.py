"""Add integrations tables: integrations, webhooks, webhook_deliveries, integration_logs

Revision ID: add_integrations_tables
Revises: add_search_tables
Create Date: 2025-01-17 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_integrations_tables"
down_revision: Union[str, None] = "add_search_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create integrations table
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("integration_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_sync_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integrations_tenant_id", "integrations", ["tenant_id"], unique=False)
    op.create_index("ix_integrations_integration_type", "integrations", ["integration_type"], unique=False)
    op.create_index("ix_integrations_status", "integrations", ["status"], unique=False)
    op.create_index("idx_integrations_tenant_status", "integrations", ["tenant_id", "status"], unique=False)
    op.create_index("idx_integrations_tenant_type", "integrations", ["tenant_id", "integration_type"], unique=False)

    # Create webhooks table
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("method", sa.String(length=10), nullable=False, server_default="POST"),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("secret", sa.String(length=255), nullable=True),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_delay", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhooks_tenant_id", "webhooks", ["tenant_id"], unique=False)
    op.create_index("ix_webhooks_integration_id", "webhooks", ["integration_id"], unique=False)
    op.create_index("ix_webhooks_event_type", "webhooks", ["event_type"], unique=False)
    op.create_index("ix_webhooks_enabled", "webhooks", ["enabled"], unique=False)
    op.create_index("idx_webhooks_tenant_event", "webhooks", ["tenant_id", "event_type"], unique=False)
    op.create_index("idx_webhooks_tenant_enabled", "webhooks", ["tenant_id", "enabled"], unique=False)

    # Create webhook_deliveries table
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"], unique=False)
    op.create_index("ix_webhook_deliveries_tenant_id", "webhook_deliveries", ["tenant_id"], unique=False)
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"], unique=False)
    op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"], unique=False)
    op.create_index("idx_webhook_deliveries_webhook_status", "webhook_deliveries", ["webhook_id", "status"], unique=False)
    op.create_index("idx_webhook_deliveries_tenant_created", "webhook_deliveries", ["tenant_id", "created_at"], unique=False)
    op.create_index("idx_webhook_deliveries_retry", "webhook_deliveries", ["status", "next_retry_at"], unique=False)

    # Create integration_logs table
    op.create_table(
        "integration_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_logs_integration_id", "integration_logs", ["integration_id"], unique=False)
    op.create_index("ix_integration_logs_tenant_id", "integration_logs", ["tenant_id"], unique=False)
    op.create_index("ix_integration_logs_created_at", "integration_logs", ["created_at"], unique=False)
    op.create_index("idx_integration_logs_integration_created", "integration_logs", ["integration_id", "created_at"], unique=False)
    op.create_index("idx_integration_logs_tenant_created", "integration_logs", ["tenant_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_integration_logs_tenant_created", table_name="integration_logs")
    op.drop_index("idx_integration_logs_integration_created", table_name="integration_logs")
    op.drop_index("ix_integration_logs_created_at", table_name="integration_logs")
    op.drop_index("ix_integration_logs_tenant_id", table_name="integration_logs")
    op.drop_index("ix_integration_logs_integration_id", table_name="integration_logs")
    op.drop_table("integration_logs")

    op.drop_index("idx_webhook_deliveries_retry", table_name="webhook_deliveries")
    op.drop_index("idx_webhook_deliveries_tenant_created", table_name="webhook_deliveries")
    op.drop_index("idx_webhook_deliveries_webhook_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_created_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("idx_webhooks_tenant_enabled", table_name="webhooks")
    op.drop_index("idx_webhooks_tenant_event", table_name="webhooks")
    op.drop_index("ix_webhooks_enabled", table_name="webhooks")
    op.drop_index("ix_webhooks_event_type", table_name="webhooks")
    op.drop_index("ix_webhooks_integration_id", table_name="webhooks")
    op.drop_index("ix_webhooks_tenant_id", table_name="webhooks")
    op.drop_table("webhooks")

    op.drop_index("idx_integrations_tenant_type", table_name="integrations")
    op.drop_index("idx_integrations_tenant_status", table_name="integrations")
    op.drop_index("ix_integrations_status", table_name="integrations")
    op.drop_index("ix_integrations_integration_type", table_name="integrations")
    op.drop_index("ix_integrations_tenant_id", table_name="integrations")
    op.drop_table("integrations")

