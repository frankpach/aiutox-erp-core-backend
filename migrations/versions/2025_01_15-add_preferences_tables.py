"""Add preferences tables: user_preferences, org_preferences, role_preferences, saved_views, dashboards

Revision ID: add_preferences_tables
Revises: add_automation_tables
Create Date: 2025-01-15 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_preferences_tables"
down_revision: str | None = "add_automation_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create user_preferences table
    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preference_type", sa.String(length=50), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=False)
    op.create_index("ix_user_preferences_tenant_id", "user_preferences", ["tenant_id"], unique=False)
    op.create_index("ix_user_preferences_preference_type", "user_preferences", ["preference_type"], unique=False)
    op.create_index("idx_user_preferences_user_type_key", "user_preferences", ["user_id", "preference_type", "key"], unique=True)
    op.create_index("idx_user_preferences_tenant", "user_preferences", ["tenant_id"], unique=False)

    # Create org_preferences table
    op.create_table(
        "org_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preference_type", sa.String(length=50), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_preferences_tenant_id", "org_preferences", ["tenant_id"], unique=False)
    op.create_index("ix_org_preferences_preference_type", "org_preferences", ["preference_type"], unique=False)
    op.create_index("idx_org_preferences_tenant_type_key", "org_preferences", ["tenant_id", "preference_type", "key"], unique=True)

    # Create role_preferences table
    op.create_table(
        "role_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preference_type", sa.String(length=50), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["role_id"], ["module_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_preferences_role_id", "role_preferences", ["role_id"], unique=False)
    op.create_index("ix_role_preferences_tenant_id", "role_preferences", ["tenant_id"], unique=False)
    op.create_index("ix_role_preferences_preference_type", "role_preferences", ["preference_type"], unique=False)
    op.create_index("idx_role_preferences_role_type_key", "role_preferences", ["role_id", "preference_type", "key"], unique=True)
    op.create_index("idx_role_preferences_tenant", "role_preferences", ["tenant_id"], unique=False)

    # Create saved_views table
    op.create_table(
        "saved_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_views_user_id", "saved_views", ["user_id"], unique=False)
    op.create_index("ix_saved_views_tenant_id", "saved_views", ["tenant_id"], unique=False)
    op.create_index("ix_saved_views_module", "saved_views", ["module"], unique=False)
    op.create_index("idx_saved_views_user_module", "saved_views", ["user_id", "module"], unique=False)
    op.create_index("idx_saved_views_tenant", "saved_views", ["tenant_id"], unique=False)

    # Create dashboards table
    op.create_table(
        "dashboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("widgets", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboards_user_id", "dashboards", ["user_id"], unique=False)
    op.create_index("ix_dashboards_tenant_id", "dashboards", ["tenant_id"], unique=False)
    op.create_index("idx_dashboards_user", "dashboards", ["user_id"], unique=False)
    op.create_index("idx_dashboards_tenant", "dashboards", ["tenant_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_dashboards_tenant", table_name="dashboards")
    op.drop_index("idx_dashboards_user", table_name="dashboards")
    op.drop_index("ix_dashboards_tenant_id", table_name="dashboards")
    op.drop_index("ix_dashboards_user_id", table_name="dashboards")
    op.drop_index("idx_saved_views_tenant", table_name="saved_views")
    op.drop_index("idx_saved_views_user_module", table_name="saved_views")
    op.drop_index("ix_saved_views_module", table_name="saved_views")
    op.drop_index("ix_saved_views_tenant_id", table_name="saved_views")
    op.drop_index("ix_saved_views_user_id", table_name="saved_views")
    op.drop_index("idx_role_preferences_tenant", table_name="role_preferences")
    op.drop_index("idx_role_preferences_role_type_key", table_name="role_preferences")
    op.drop_index("ix_role_preferences_preference_type", table_name="role_preferences")
    op.drop_index("ix_role_preferences_tenant_id", table_name="role_preferences")
    op.drop_index("ix_role_preferences_role_id", table_name="role_preferences")
    op.drop_index("idx_org_preferences_tenant_type_key", table_name="org_preferences")
    op.drop_index("ix_org_preferences_preference_type", table_name="org_preferences")
    op.drop_index("ix_org_preferences_tenant_id", table_name="org_preferences")
    op.drop_index("idx_user_preferences_tenant", table_name="user_preferences")
    op.drop_index("idx_user_preferences_user_type_key", table_name="user_preferences")
    op.drop_index("ix_user_preferences_preference_type", table_name="user_preferences")
    op.drop_index("ix_user_preferences_tenant_id", table_name="user_preferences")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")

    # Drop tables
    op.drop_table("dashboards")
    op.drop_table("saved_views")
    op.drop_table("role_preferences")
    op.drop_table("org_preferences")
    op.drop_table("user_preferences")










