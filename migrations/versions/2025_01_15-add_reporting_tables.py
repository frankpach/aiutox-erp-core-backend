"""Add reporting tables: report_definitions, dashboard_widgets

Revision ID: add_reporting_tables
Revises: add_preferences_tables
Create Date: 2025-01-15 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_reporting_tables"
down_revision: Union[str, None] = "add_preferences_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create report_definitions table
    op.create_table(
        "report_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_source_type", sa.String(length=100), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("visualization_type", sa.String(length=50), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_definitions_tenant_id", "report_definitions", ["tenant_id"], unique=False)
    op.create_index("ix_report_definitions_data_source_type", "report_definitions", ["data_source_type"], unique=False)
    op.create_index("ix_report_definitions_created_by", "report_definitions", ["created_by"], unique=False)
    op.create_index("idx_report_definitions_tenant", "report_definitions", ["tenant_id"], unique=False)
    op.create_index("idx_report_definitions_data_source", "report_definitions", ["data_source_type"], unique=False)

    # Create dashboard_widgets table
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dashboard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_definition_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("size", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_definition_id"], ["report_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_widgets_dashboard_id", "dashboard_widgets", ["dashboard_id"], unique=False)
    op.create_index("ix_dashboard_widgets_report_definition_id", "dashboard_widgets", ["report_definition_id"], unique=False)
    op.create_index("idx_dashboard_widgets_dashboard", "dashboard_widgets", ["dashboard_id"], unique=False)
    op.create_index("idx_dashboard_widgets_report", "dashboard_widgets", ["report_definition_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_dashboard_widgets_report", table_name="dashboard_widgets")
    op.drop_index("idx_dashboard_widgets_dashboard", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_report_definition_id", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_dashboard_id", table_name="dashboard_widgets")
    op.drop_index("idx_report_definitions_data_source", table_name="report_definitions")
    op.drop_index("idx_report_definitions_tenant", table_name="report_definitions")
    op.drop_index("ix_report_definitions_created_by", table_name="report_definitions")
    op.drop_index("ix_report_definitions_data_source_type", table_name="report_definitions")
    op.drop_index("ix_report_definitions_tenant_id", table_name="report_definitions")

    # Drop tables
    op.drop_table("dashboard_widgets")
    op.drop_table("report_definitions")










