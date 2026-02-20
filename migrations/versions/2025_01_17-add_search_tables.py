"""Add search tables: search_indices

Revision ID: add_search_tables
Revises: add_tasks_tables
Create Date: 2025-01-17 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_search_tables"
down_revision: str | None = "add_tasks_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create search_indices table
    op.create_table(
        "search_indices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_indices_tenant_id", "search_indices", ["tenant_id"], unique=False)
    op.create_index("ix_search_indices_entity_type", "search_indices", ["entity_type"], unique=False)
    op.create_index("ix_search_indices_entity_id", "search_indices", ["entity_id"], unique=False)
    op.create_index("ix_search_indices_created_at", "search_indices", ["created_at"], unique=False)
    op.create_index("idx_search_indices_entity", "search_indices", ["entity_type", "entity_id"], unique=True)
    op.create_index("idx_search_indices_tenant_entity", "search_indices", ["tenant_id", "entity_type", "entity_id"], unique=False)
    # Note: GIN index for search_vector would be created manually or via raw SQL if needed
    # For now, we'll use regular indexes


def downgrade() -> None:
    op.drop_index("idx_search_indices_tenant_entity", table_name="search_indices")
    op.drop_index("idx_search_indices_entity", table_name="search_indices")
    op.drop_index("ix_search_indices_created_at", table_name="search_indices")
    op.drop_index("ix_search_indices_entity_id", table_name="search_indices")
    op.drop_index("ix_search_indices_entity_type", table_name="search_indices")
    op.drop_index("ix_search_indices_tenant_id", table_name="search_indices")
    op.drop_table("search_indices")

