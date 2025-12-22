"""Add integrations table

Revision ID: 2025_12_21-add_integrations
Revises: 2025_12_21_config_versions
Create Date: 2025-12-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2025_12_21-add_integrations"
down_revision: Union[str, None] = "2025_12_21_config_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create integrations table."""
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="inactive"),
        sa.Column("config", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_integrations_tenant_id", "tenant_id"),
        sa.Index("ix_integrations_type", "type"),
        sa.Index("ix_integrations_status", "status"),
    )


def downgrade() -> None:
    """Drop integrations table."""
    op.drop_table("integrations")

