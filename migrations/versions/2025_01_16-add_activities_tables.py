"""Add activities table: activities

Revision ID: add_activities_tables
Revises: add_files_tables
Create Date: 2025-01-16 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_activities_tables"
down_revision: Union[str, None] = "add_files_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create activities table
    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_tenant_id", "activities", ["tenant_id"], unique=False)
    op.create_index("ix_activities_entity_type", "activities", ["entity_type"], unique=False)
    op.create_index("ix_activities_entity_id", "activities", ["entity_id"], unique=False)
    op.create_index("ix_activities_activity_type", "activities", ["activity_type"], unique=False)
    op.create_index("ix_activities_user_id", "activities", ["user_id"], unique=False)
    op.create_index("ix_activities_created_at", "activities", ["created_at"], unique=False)
    op.create_index("idx_activities_entity", "activities", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_activities_tenant_entity", "activities", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("idx_activities_created", "activities", ["tenant_id", "created_at"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_activities_created", table_name="activities")
    op.drop_index("idx_activities_tenant_entity", table_name="activities")
    op.drop_index("idx_activities_entity", table_name="activities")
    op.drop_index("ix_activities_created_at", table_name="activities")
    op.drop_index("ix_activities_user_id", table_name="activities")
    op.drop_index("ix_activities_activity_type", table_name="activities")
    op.drop_index("ix_activities_entity_id", table_name="activities")
    op.drop_index("ix_activities_entity_type", table_name="activities")
    op.drop_index("ix_activities_tenant_id", table_name="activities")

    # Drop table
    op.drop_table("activities")

