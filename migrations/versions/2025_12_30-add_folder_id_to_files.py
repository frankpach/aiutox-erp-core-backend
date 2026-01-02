"""Add folder_id column to files table

Revision ID: add_folder_id_to_files
Revises: add_files_tables
Create Date: 2025-12-30 19:52:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_folder_id_to_files"
down_revision: Union[str, None] = "add_files_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if folders table exists, if not create it first
    # (This handles the case where folders table might not exist yet)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "folders" not in tables:
        # Create folders table first
        op.create_table(
            "folders",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("color", sa.String(length=7), nullable=True),
            sa.Column("icon", sa.String(length=50), nullable=True),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("entity_type", sa.String(length=50), nullable=True),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_folders_tenant_id", "folders", ["tenant_id"], unique=False)
        op.create_index("ix_folders_parent_id", "folders", ["parent_id"], unique=False)
        op.create_index("ix_folders_entity_type", "folders", ["entity_type"], unique=False)
        op.create_index("ix_folders_entity_id", "folders", ["entity_id"], unique=False)
        op.create_index("ix_folders_created_at", "folders", ["created_at"], unique=False)

    # Add folder_id column to files table
    op.add_column(
        "files",
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_files_folder_id",
        "files",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index
    op.create_index("ix_files_folder_id", "files", ["folder_id"], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_files_folder_id", table_name="files")

    # Drop foreign key constraint
    op.drop_constraint("fk_files_folder_id", "files", type_="foreignkey")

    # Drop column
    op.drop_column("files", "folder_id")

    # Note: We don't drop the folders table in downgrade as it might be used elsewhere


