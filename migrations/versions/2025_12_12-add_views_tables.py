"""Add views tables: saved_filters, custom_views, view_shares

Revision ID: add_views_tables
Revises: add_import_export_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_views_tables"
down_revision: Union[str, None] = "add_import_export_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create saved_filters table
    op.create_table(
        "saved_filters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_filters_tenant_id", "saved_filters", ["tenant_id"], unique=False)
    op.create_index("ix_saved_filters_module", "saved_filters", ["module"], unique=False)
    op.create_index("ix_saved_filters_created_by", "saved_filters", ["created_by"], unique=False)
    op.create_index("idx_saved_filters_tenant_module", "saved_filters", ["tenant_id", "module"], unique=False)
    op.create_index("idx_saved_filters_user", "saved_filters", ["tenant_id", "created_by"], unique=False)

    # Create custom_views table
    op.create_table(
        "custom_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("columns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sorting", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("grouping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_views_tenant_id", "custom_views", ["tenant_id"], unique=False)
    op.create_index("ix_custom_views_module", "custom_views", ["module"], unique=False)
    op.create_index("ix_custom_views_created_by", "custom_views", ["created_by"], unique=False)
    op.create_index("idx_custom_views_tenant_module", "custom_views", ["tenant_id", "module"], unique=False)
    op.create_index("idx_custom_views_user", "custom_views", ["tenant_id", "created_by"], unique=False)

    # Create view_shares table
    op.create_table(
        "view_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("view_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shared_with_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shared_with_role", sa.String(length=50), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shared_with_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_view_shares_tenant_id", "view_shares", ["tenant_id"], unique=False)
    op.create_index("ix_view_shares_filter_id", "view_shares", ["filter_id"], unique=False)
    op.create_index("ix_view_shares_view_id", "view_shares", ["view_id"], unique=False)
    op.create_index("ix_view_shares_shared_with_user_id", "view_shares", ["shared_with_user_id"], unique=False)
    op.create_index("idx_view_shares_filter", "view_shares", ["tenant_id", "filter_id"], unique=False)
    op.create_index("idx_view_shares_view", "view_shares", ["tenant_id", "view_id"], unique=False)
    op.create_index("idx_view_shares_user", "view_shares", ["tenant_id", "shared_with_user_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_view_shares_user", table_name="view_shares")
    op.drop_index("idx_view_shares_view", table_name="view_shares")
    op.drop_index("idx_view_shares_filter", table_name="view_shares")
    op.drop_index("ix_view_shares_shared_with_user_id", table_name="view_shares")
    op.drop_index("ix_view_shares_view_id", table_name="view_shares")
    op.drop_index("ix_view_shares_filter_id", table_name="view_shares")
    op.drop_index("ix_view_shares_tenant_id", table_name="view_shares")
    op.drop_table("view_shares")

    op.drop_index("idx_custom_views_user", table_name="custom_views")
    op.drop_index("idx_custom_views_tenant_module", table_name="custom_views")
    op.drop_index("ix_custom_views_created_by", table_name="custom_views")
    op.drop_index("ix_custom_views_module", table_name="custom_views")
    op.drop_index("ix_custom_views_tenant_id", table_name="custom_views")
    op.drop_table("custom_views")

    op.drop_index("idx_saved_filters_user", table_name="saved_filters")
    op.drop_index("idx_saved_filters_tenant_module", table_name="saved_filters")
    op.drop_index("ix_saved_filters_created_by", table_name="saved_filters")
    op.drop_index("ix_saved_filters_module", table_name="saved_filters")
    op.drop_index("ix_saved_filters_tenant_id", table_name="saved_filters")
    op.drop_table("saved_filters")

