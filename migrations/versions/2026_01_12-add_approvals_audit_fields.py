"""Add soft delete and audit fields to approvals tables

Revision ID: add_approvals_audit_fields
Revises: add_approvals_tables
Create Date: 2026-01-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_approvals_audit_fields"
down_revision: Union[str, None] = "add_approvals_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete and audit fields to approval_flows
    op.add_column(
        "approval_flows",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "approval_flows",
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_approval_flows_updated_by", "approval_flows", ["updated_by"], unique=False)
    op.create_index("ix_approval_flows_deleted_at", "approval_flows", ["deleted_at"], unique=False)
    op.create_foreign_key(
        "fk_approval_flows_updated_by_users",
        "approval_flows",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add audit fields to approval_actions
    op.add_column(
        "approval_actions",
        sa.Column("ip_address", sa.String(length=45), nullable=True),
    )
    op.add_column(
        "approval_actions",
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_approval_actions_ip_address", "approval_actions", ["ip_address"], unique=False)


def downgrade() -> None:
    # Remove audit fields from approval_actions
    op.drop_index("ix_approval_actions_ip_address", table_name="approval_actions")
    op.drop_column("approval_actions", "user_agent")
    op.drop_column("approval_actions", "ip_address")

    # Remove soft delete and audit fields from approval_flows
    op.drop_constraint("fk_approval_flows_updated_by_users", "approval_flows", type_="foreignkey")
    op.drop_index("ix_approval_flows_deleted_at", table_name="approval_flows")
    op.drop_index("ix_approval_flows_updated_by", table_name="approval_flows")
    op.drop_column("approval_flows", "deleted_at")
    op.drop_column("approval_flows", "updated_by")
