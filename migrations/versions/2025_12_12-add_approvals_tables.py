"""Add approvals tables: approval_flows, approval_steps, approval_requests, approval_actions, approval_delegations

Revision ID: add_approvals_tables
Revises: add_views_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_approvals_tables"
down_revision: Union[str, None] = "add_views_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create approval_flows table
    op.create_table(
        "approval_flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flow_type", sa.String(length=20), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_flows_tenant_id", "approval_flows", ["tenant_id"], unique=False)
    op.create_index("ix_approval_flows_module", "approval_flows", ["module"], unique=False)
    op.create_index("ix_approval_flows_created_by", "approval_flows", ["created_by"], unique=False)
    op.create_index("idx_approval_flows_tenant_module", "approval_flows", ["tenant_id", "module"], unique=False)

    # Create approval_steps table
    op.create_table(
        "approval_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("approver_type", sa.String(length=20), nullable=False),
        sa.Column("approver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approver_role", sa.String(length=50), nullable=True),
        sa.Column("approver_rule", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("require_all", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_approvals", sa.Integer(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flow_id"], ["approval_flows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_steps_tenant_id", "approval_steps", ["tenant_id"], unique=False)
    op.create_index("ix_approval_steps_flow_id", "approval_steps", ["flow_id"], unique=False)
    op.create_index("idx_approval_steps_flow_order", "approval_steps", ["flow_id", "step_order"], unique=False)

    # Create approval_requests table
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("requested_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flow_id"], ["approval_flows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_tenant_id", "approval_requests", ["tenant_id"], unique=False)
    op.create_index("ix_approval_requests_flow_id", "approval_requests", ["flow_id"], unique=False)
    op.create_index("ix_approval_requests_entity_type", "approval_requests", ["entity_type"], unique=False)
    op.create_index("ix_approval_requests_entity_id", "approval_requests", ["entity_id"], unique=False)
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"], unique=False)
    op.create_index("ix_approval_requests_requested_by", "approval_requests", ["requested_by"], unique=False)
    op.create_index("ix_approval_requests_requested_at", "approval_requests", ["requested_at"], unique=False)
    op.create_index("idx_approval_requests_entity", "approval_requests", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_approval_requests_status", "approval_requests", ["tenant_id", "status"], unique=False)
    op.create_index("idx_approval_requests_flow", "approval_requests", ["flow_id", "status"], unique=False)

    # Create approval_actions table
    op.create_table(
        "approval_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("acted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("acted_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["approval_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["acted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_actions_tenant_id", "approval_actions", ["tenant_id"], unique=False)
    op.create_index("ix_approval_actions_request_id", "approval_actions", ["request_id"], unique=False)
    op.create_index("ix_approval_actions_acted_by", "approval_actions", ["acted_by"], unique=False)
    op.create_index("ix_approval_actions_acted_at", "approval_actions", ["acted_at"], unique=False)
    op.create_index("idx_approval_actions_request", "approval_actions", ["request_id", "acted_at"], unique=False)

    # Create approval_delegations table
    op.create_table(
        "approval_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["approval_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_delegations_tenant_id", "approval_delegations", ["tenant_id"], unique=False)
    op.create_index("ix_approval_delegations_request_id", "approval_delegations", ["request_id"], unique=False)
    op.create_index("ix_approval_delegations_from_user_id", "approval_delegations", ["from_user_id"], unique=False)
    op.create_index("ix_approval_delegations_to_user_id", "approval_delegations", ["to_user_id"], unique=False)
    op.create_index("ix_approval_delegations_is_active", "approval_delegations", ["is_active"], unique=False)
    op.create_index("idx_approval_delegations_active", "approval_delegations", ["tenant_id", "is_active"], unique=False)
    op.create_index("idx_approval_delegations_from", "approval_delegations", ["from_user_id", "is_active"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_approval_delegations_from", table_name="approval_delegations")
    op.drop_index("idx_approval_delegations_active", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_is_active", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_to_user_id", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_from_user_id", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_request_id", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_tenant_id", table_name="approval_delegations")
    op.drop_table("approval_delegations")

    op.drop_index("idx_approval_actions_request", table_name="approval_actions")
    op.drop_index("ix_approval_actions_acted_at", table_name="approval_actions")
    op.drop_index("ix_approval_actions_acted_by", table_name="approval_actions")
    op.drop_index("ix_approval_actions_request_id", table_name="approval_actions")
    op.drop_index("ix_approval_actions_tenant_id", table_name="approval_actions")
    op.drop_table("approval_actions")

    op.drop_index("idx_approval_requests_flow", table_name="approval_requests")
    op.drop_index("idx_approval_requests_status", table_name="approval_requests")
    op.drop_index("idx_approval_requests_entity", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_by", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_entity_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_entity_type", table_name="approval_requests")
    op.drop_index("ix_approval_requests_flow_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tenant_id", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("idx_approval_steps_flow_order", table_name="approval_steps")
    op.drop_index("ix_approval_steps_flow_id", table_name="approval_steps")
    op.drop_index("ix_approval_steps_tenant_id", table_name="approval_steps")
    op.drop_table("approval_steps")

    op.drop_index("idx_approval_flows_tenant_module", table_name="approval_flows")
    op.drop_index("ix_approval_flows_created_by", table_name="approval_flows")
    op.drop_index("ix_approval_flows_module", table_name="approval_flows")
    op.drop_index("ix_approval_flows_tenant_id", table_name="approval_flows")
    op.drop_table("approval_flows")








