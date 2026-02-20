"""Add form and print configuration to approval_steps

Revision ID: add_steps_form_print_config
Revises: add_approvals_audit_fields
Create Date: 2026-01-12 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_steps_form_print_config"
down_revision: str | None = "add_approvals_audit_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add form and print configuration columns to approval_steps
    op.add_column(
        "approval_steps",
        sa.Column("form_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "approval_steps",
        sa.Column("print_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "approval_steps",
        sa.Column("rejection_required", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    # Remove form and print configuration columns from approval_steps
    op.drop_column("approval_steps", "rejection_required")
    op.drop_column("approval_steps", "print_config")
    op.drop_column("approval_steps", "form_schema")
