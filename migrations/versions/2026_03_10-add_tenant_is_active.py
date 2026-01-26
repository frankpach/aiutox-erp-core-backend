"""Add is_active flag to tenants table

Revision ID: 2026_03_10_add_tenant_is_active
Revises: 2026_03_05_optimize_task_indexes
Create Date: 2026-03-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2026_03_10_add_tenant_is_active"
down_revision = "2026_03_05_optimize_task_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index("ix_tenants_is_active", "tenants", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_is_active", table_name="tenants")
    op.drop_column("tenants", "is_active")
