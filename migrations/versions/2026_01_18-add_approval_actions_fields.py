"""Add missing fields to approval_actions table

Revision ID: add_approval_actions_fields
Revises: add_approvals_audit_fields
Create Date: 2026-01-18 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_approval_actions_fields"
down_revision: str | None = "add_approvals_audit_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing fields to approval_actions
    op.add_column(
        "approval_actions",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        schema=None,
    )
    op.add_column(
        "approval_actions",
        sa.Column("form_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=None,
    )
    op.add_column(
        "approval_actions",
        sa.Column("request_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema=None,
    )


def downgrade() -> None:
    # Remove the added fields
    op.drop_column("approval_actions", "request_metadata", schema=None)
    op.drop_column("approval_actions", "form_data", schema=None)
    op.drop_column("approval_actions", "rejection_reason", schema=None)
