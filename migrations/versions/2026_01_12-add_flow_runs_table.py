"""Add flow_runs table for tracking workflow executions

Revision ID: add_flow_runs_table
Revises: add_steps_form_print_config
Create Date: 2026-01-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_flow_runs_table"
down_revision: Union[str, None] = "add_steps_form_print_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create flow_runs table
    op.create_table(
        "flow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flow_id"], ["approval_flows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flow_runs_tenant_id", "flow_runs", ["tenant_id"], unique=False)
    op.create_index("ix_flow_runs_flow_id", "flow_runs", ["flow_id"], unique=False)
    op.create_index("ix_flow_runs_entity_type", "flow_runs", ["entity_type"], unique=False)
    op.create_index("ix_flow_runs_entity_id", "flow_runs", ["entity_id"], unique=False)
    op.create_index("ix_flow_runs_status", "flow_runs", ["status"], unique=False)
    op.create_index("idx_flow_runs_tenant_entity", "flow_runs", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("idx_flow_runs_status_tenant", "flow_runs", ["status", "tenant_id"], unique=False)
    op.create_index("idx_flow_runs_flow_tenant", "flow_runs", ["flow_id", "tenant_id"], unique=False)


def downgrade() -> None:
    # Drop flow_runs table
    op.drop_table("flow_runs")
