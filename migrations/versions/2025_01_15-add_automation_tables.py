"""Add automation tables: rules, rule_versions, automation_executions

Revision ID: add_automation_tables
Revises: a8ae578ac76b
Create Date: 2025-01-15 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_automation_tables"
down_revision: Union[str, None] = "a8ae578ac76b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create rules table
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("trigger", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rules_tenant_id", "rules", ["tenant_id"], unique=False)
    op.create_index("ix_rules_enabled", "rules", ["enabled"], unique=False)
    op.create_index("idx_rules_tenant_enabled", "rules", ["tenant_id", "enabled"], unique=False)

    # Create rule_versions table
    op.create_table(
        "rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rule_versions_rule_id", "rule_versions", ["rule_id"], unique=False)
    op.create_index("idx_rule_versions_rule_version", "rule_versions", ["rule_id", "version"], unique=True)

    # Create automation_executions table
    op.create_table(
        "automation_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("executed_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_executions_rule_id", "automation_executions", ["rule_id"], unique=False)
    op.create_index("ix_automation_executions_event_id", "automation_executions", ["event_id"], unique=True)
    op.create_index("ix_automation_executions_status", "automation_executions", ["status"], unique=False)
    op.create_index("idx_automation_executions_rule_status", "automation_executions", ["rule_id", "status"], unique=False)
    op.create_index("idx_automation_executions_executed_at", "automation_executions", ["executed_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_automation_executions_executed_at", table_name="automation_executions")
    op.drop_index("idx_automation_executions_rule_status", table_name="automation_executions")
    op.drop_index("ix_automation_executions_status", table_name="automation_executions")
    op.drop_index("ix_automation_executions_event_id", table_name="automation_executions")
    op.drop_index("ix_automation_executions_rule_id", table_name="automation_executions")
    op.drop_index("idx_rule_versions_rule_version", table_name="rule_versions")
    op.drop_index("ix_rule_versions_rule_id", table_name="rule_versions")
    op.drop_index("idx_rules_tenant_enabled", table_name="rules")
    op.drop_index("ix_rules_enabled", table_name="rules")
    op.drop_index("ix_rules_tenant_id", table_name="rules")

    # Drop tables
    op.drop_table("automation_executions")
    op.drop_table("rule_versions")
    op.drop_table("rules")









