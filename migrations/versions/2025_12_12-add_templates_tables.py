"""Add templates tables: templates, template_versions, template_categories

Revision ID: add_templates_tables
Revises: add_approvals_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_templates_tables"
down_revision: Union[str, None] = "add_approvals_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create templates table
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(length=20), nullable=False),
        sa.Column("template_format", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_tenant_id", "templates", ["tenant_id"], unique=False)
    op.create_index("ix_templates_template_type", "templates", ["template_type"], unique=False)
    op.create_index("ix_templates_category", "templates", ["category"], unique=False)
    op.create_index("ix_templates_created_by", "templates", ["created_by"], unique=False)
    op.create_index("idx_templates_tenant_type", "templates", ["tenant_id", "template_type"], unique=False)
    op.create_index("idx_templates_category", "templates", ["tenant_id", "category"], unique=False)

    # Create template_versions table
    op.create_table(
        "template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_template_versions_tenant_id", "template_versions", ["tenant_id"], unique=False)
    op.create_index("ix_template_versions_template_id", "template_versions", ["template_id"], unique=False)
    op.create_index("ix_template_versions_is_current", "template_versions", ["is_current"], unique=False)
    op.create_index("ix_template_versions_created_by", "template_versions", ["created_by"], unique=False)
    op.create_index("idx_template_versions_template", "template_versions", ["template_id", "version_number"], unique=False)
    op.create_index("idx_template_versions_current", "template_versions", ["template_id", "is_current"], unique=False)

    # Create template_categories table
    op.create_table(
        "template_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["template_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_template_categories_tenant_id", "template_categories", ["tenant_id"], unique=False)
    op.create_index("idx_template_categories_tenant", "template_categories", ["tenant_id", "name"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_template_categories_tenant", table_name="template_categories")
    op.drop_index("ix_template_categories_tenant_id", table_name="template_categories")
    op.drop_table("template_categories")

    op.drop_index("idx_template_versions_current", table_name="template_versions")
    op.drop_index("idx_template_versions_template", table_name="template_versions")
    op.drop_index("ix_template_versions_created_by", table_name="template_versions")
    op.drop_index("ix_template_versions_is_current", table_name="template_versions")
    op.drop_index("ix_template_versions_template_id", table_name="template_versions")
    op.drop_index("ix_template_versions_tenant_id", table_name="template_versions")
    op.drop_table("template_versions")

    op.drop_index("idx_templates_category", table_name="templates")
    op.drop_index("idx_templates_tenant_type", table_name="templates")
    op.drop_index("ix_templates_created_by", table_name="templates")
    op.drop_index("ix_templates_category", table_name="templates")
    op.drop_index("ix_templates_template_type", table_name="templates")
    op.drop_index("ix_templates_tenant_id", table_name="templates")
    op.drop_table("templates")








