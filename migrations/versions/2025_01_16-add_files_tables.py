"""Add files tables: files, file_versions, file_permissions

Revision ID: add_files_tables
Revises: add_notifications_tables
Create Date: 2025-01-16 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_files_tables"
down_revision: str | None = "add_notifications_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create files table
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("extension", sa.String(length=10), nullable=True),
        sa.Column("storage_backend", sa.String(length=20), nullable=False, server_default="local"),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("storage_url", sa.String(length=1000), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_tenant_id", "files", ["tenant_id"], unique=False)
    op.create_index("ix_files_entity_type", "files", ["entity_type"], unique=False)
    op.create_index("ix_files_entity_id", "files", ["entity_id"], unique=False)
    op.create_index("ix_files_uploaded_by", "files", ["uploaded_by"], unique=False)
    op.create_index("ix_files_is_current", "files", ["is_current"], unique=False)
    op.create_index("ix_files_created_at", "files", ["created_at"], unique=False)
    op.create_index("idx_files_entity", "files", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_files_tenant_entity", "files", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("idx_files_current", "files", ["tenant_id", "is_current"], unique=False)

    # Create file_versions table
    op.create_table(
        "file_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("storage_backend", sa.String(length=20), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_versions_file_id", "file_versions", ["file_id"], unique=False)
    op.create_index("ix_file_versions_tenant_id", "file_versions", ["tenant_id"], unique=False)
    op.create_index("ix_file_versions_created_at", "file_versions", ["created_at"], unique=False)
    op.create_index("idx_file_versions_file", "file_versions", ["file_id", "version_number"], unique=False)

    # Create file_permissions table
    op.create_table(
        "file_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("can_view", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_download", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_edit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("can_delete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_permissions_file_id", "file_permissions", ["file_id"], unique=False)
    op.create_index("ix_file_permissions_tenant_id", "file_permissions", ["tenant_id"], unique=False)
    op.create_index("idx_file_permissions_file", "file_permissions", ["file_id"], unique=False)
    op.create_index("idx_file_permissions_target", "file_permissions", ["target_type", "target_id"], unique=False)
    op.create_index("idx_file_permissions_tenant", "file_permissions", ["tenant_id", "target_type", "target_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_file_permissions_tenant", table_name="file_permissions")
    op.drop_index("idx_file_permissions_target", table_name="file_permissions")
    op.drop_index("idx_file_permissions_file", table_name="file_permissions")
    op.drop_index("ix_file_permissions_tenant_id", table_name="file_permissions")
    op.drop_index("ix_file_permissions_file_id", table_name="file_permissions")
    op.drop_index("idx_file_versions_file", table_name="file_versions")
    op.drop_index("ix_file_versions_created_at", table_name="file_versions")
    op.drop_index("ix_file_versions_tenant_id", table_name="file_versions")
    op.drop_index("ix_file_versions_file_id", table_name="file_versions")
    op.drop_index("idx_files_current", table_name="files")
    op.drop_index("idx_files_tenant_entity", table_name="files")
    op.drop_index("idx_files_entity", table_name="files")
    op.drop_index("ix_files_created_at", table_name="files")
    op.drop_index("ix_files_is_current", table_name="files")
    op.drop_index("ix_files_uploaded_by", table_name="files")
    op.drop_index("ix_files_entity_id", table_name="files")
    op.drop_index("ix_files_entity_type", table_name="files")
    op.drop_index("ix_files_tenant_id", table_name="files")

    # Drop tables
    op.drop_table("file_permissions")
    op.drop_table("file_versions")
    op.drop_table("files")

