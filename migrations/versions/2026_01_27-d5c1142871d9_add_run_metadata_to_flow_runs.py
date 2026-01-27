"""add_run_metadata_to_flow_runs

Revision ID: d5c1142871d9
Revises: 2026_03_10_add_tenant_is_active
Create Date: 2026-01-27 16:53:48.678624+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5c1142871d9'
down_revision: str | None = '2026_03_10_add_tenant_is_active'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add run_metadata column to flow_runs table
    op.add_column('flow_runs', sa.Column('run_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove run_metadata column from flow_runs table
    op.drop_column('flow_runs', 'run_metadata')

