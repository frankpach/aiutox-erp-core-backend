"""Add tags tables: tags, tag_categories, entity_tags

Revision ID: add_tags_tables
Revises: add_activities_tables
Create Date: 2025-01-16 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_tags_tables"
down_revision: str | None = "add_activities_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create tag_categories table (must be created before tags due to FK)
    op.create_table(
        "tag_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["tag_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tag_categories_tenant_id", "tag_categories", ["tenant_id"], unique=False)
    op.create_index("idx_tag_categories_tenant_name", "tag_categories", ["tenant_id", "name"], unique=True)

    # Create tags table
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["tag_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_tenant_id", "tags", ["tenant_id"], unique=False)
    op.create_index("ix_tags_name", "tags", ["name"], unique=False)
    op.create_index("ix_tags_category_id", "tags", ["category_id"], unique=False)
    op.create_index("ix_tags_is_active", "tags", ["is_active"], unique=False)
    op.create_index("idx_tags_tenant_name", "tags", ["tenant_id", "name"], unique=True)
    op.create_index("idx_tags_category", "tags", ["tenant_id", "category_id"], unique=False)

    # Create entity_tags table
    op.create_table(
        "entity_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_tags_tenant_id", "entity_tags", ["tenant_id"], unique=False)
    op.create_index("ix_entity_tags_tag_id", "entity_tags", ["tag_id"], unique=False)
    op.create_index("ix_entity_tags_entity_type", "entity_tags", ["entity_type"], unique=False)
    op.create_index("ix_entity_tags_entity_id", "entity_tags", ["entity_id"], unique=False)
    op.create_index("idx_entity_tags_entity", "entity_tags", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_entity_tags_tag", "entity_tags", ["tag_id"], unique=False)
    op.create_index("idx_entity_tags_tenant_entity", "entity_tags", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("idx_entity_tags_unique", "entity_tags", ["tag_id", "entity_type", "entity_id"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_entity_tags_unique", table_name="entity_tags")
    op.drop_index("idx_entity_tags_tenant_entity", table_name="entity_tags")
    op.drop_index("idx_entity_tags_tag", table_name="entity_tags")
    op.drop_index("idx_entity_tags_entity", table_name="entity_tags")
    op.drop_index("ix_entity_tags_entity_id", table_name="entity_tags")
    op.drop_index("ix_entity_tags_entity_type", table_name="entity_tags")
    op.drop_index("ix_entity_tags_tag_id", table_name="entity_tags")
    op.drop_index("ix_entity_tags_tenant_id", table_name="entity_tags")
    op.drop_index("idx_tags_category", table_name="tags")
    op.drop_index("idx_tags_tenant_name", table_name="tags")
    op.drop_index("ix_tags_is_active", table_name="tags")
    op.drop_index("ix_tags_category_id", table_name="tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_index("ix_tags_tenant_id", table_name="tags")
    op.drop_index("idx_tag_categories_tenant_name", table_name="tag_categories")
    op.drop_index("ix_tag_categories_tenant_id", table_name="tag_categories")

    # Drop tables (in reverse order due to FKs)
    op.drop_table("entity_tags")
    op.drop_table("tags")
    op.drop_table("tag_categories")

