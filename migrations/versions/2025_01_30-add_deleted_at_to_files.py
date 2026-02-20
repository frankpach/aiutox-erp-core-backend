"""Add deleted_at column to files table

Revision ID: add_deleted_at_to_files
Revises: add_folder_id_to_files
Create Date: 2025-01-30 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_deleted_at_to_files"
down_revision: str | None = "add_folder_id_to_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add deleted_at column to files table
    op.add_column(
        "files",
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )

    # Add index for deleted_at
    op.create_index("idx_files_deleted_at", "files", ["deleted_at"], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_files_deleted_at", table_name="files")

    # Drop column
    op.drop_column("files", "deleted_at")






