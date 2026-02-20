"""rename_integration_type_to_type

Revision ID: 4ad0962434d7
Revises: add_calendar_tables
Create Date: 2025-12-24 20:30:52.469404+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4ad0962434d7'
down_revision: str | None = 'add_calendar_tables'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing error_message column if it doesn't exist
    # (This column exists in the model but was missing from the original migration)
    try:
        op.add_column('integrations', sa.Column('error_message', sa.Text(), nullable=True))
    except Exception:
        # Column already exists, ignore
        pass

    # Drop indexes that reference integration_type
    op.drop_index("ix_integrations_integration_type", table_name="integrations")
    op.drop_index("idx_integrations_tenant_type", table_name="integrations")

    # Rename column from integration_type to type
    op.alter_column("integrations", "integration_type", new_column_name="type")

    # Recreate indexes with new column name
    op.create_index("ix_integrations_type", "integrations", ["type"], unique=False)
    op.create_index("idx_integrations_tenant_type", "integrations", ["tenant_id", "type"], unique=False)


def downgrade() -> None:
    # Drop indexes that reference type
    op.drop_index("idx_integrations_tenant_type", table_name="integrations")
    op.drop_index("ix_integrations_type", table_name="integrations")

    # Rename column back from type to integration_type
    op.alter_column("integrations", "type", new_column_name="integration_type")

    # Recreate indexes with original column name
    op.create_index("idx_integrations_tenant_type", "integrations", ["tenant_id", "integration_type"], unique=False)
    op.create_index("ix_integrations_integration_type", "integrations", ["integration_type"], unique=False)

