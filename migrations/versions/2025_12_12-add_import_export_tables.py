"""Add import/export tables: import_jobs, import_templates, export_jobs

Revision ID: add_import_export_tables
Revises: add_calendar_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_import_export_tables"
down_revision: Union[str, None] = "add_calendar_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create import_jobs table
    op.create_table(
        "import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_tenant_id", "import_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_import_jobs_module", "import_jobs", ["module"], unique=False)
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"], unique=False)
    op.create_index("ix_import_jobs_created_by", "import_jobs", ["created_by"], unique=False)
    op.create_index("ix_import_jobs_created_at", "import_jobs", ["created_at"], unique=False)
    op.create_index("idx_import_jobs_tenant_status", "import_jobs", ["tenant_id", "status"], unique=False)
    op.create_index("idx_import_jobs_module", "import_jobs", ["tenant_id", "module"], unique=False)

    # Create import_templates table
    op.create_table(
        "import_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("field_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transformations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("skip_header", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("delimiter", sa.String(length=1), nullable=False, server_default=","),
        sa.Column("encoding", sa.String(length=20), nullable=False, server_default="utf-8"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_templates_tenant_id", "import_templates", ["tenant_id"], unique=False)
    op.create_index("ix_import_templates_module", "import_templates", ["module"], unique=False)
    op.create_index("ix_import_templates_created_by", "import_templates", ["created_by"], unique=False)
    op.create_index("idx_import_templates_tenant_module", "import_templates", ["tenant_id", "module"], unique=False)

    # Create export_jobs table
    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module", sa.String(length=50), nullable=False),
        sa.Column("export_format", sa.String(length=20), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("columns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=True),
        sa.Column("exported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_tenant_id", "export_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_export_jobs_module", "export_jobs", ["module"], unique=False)
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"], unique=False)
    op.create_index("ix_export_jobs_created_by", "export_jobs", ["created_by"], unique=False)
    op.create_index("ix_export_jobs_created_at", "export_jobs", ["created_at"], unique=False)
    op.create_index("idx_export_jobs_tenant_status", "export_jobs", ["tenant_id", "status"], unique=False)
    op.create_index("idx_export_jobs_module", "export_jobs", ["tenant_id", "module"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_export_jobs_module", table_name="export_jobs")
    op.drop_index("idx_export_jobs_tenant_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_created_at", table_name="export_jobs")
    op.drop_index("ix_export_jobs_created_by", table_name="export_jobs")
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_module", table_name="export_jobs")
    op.drop_index("ix_export_jobs_tenant_id", table_name="export_jobs")
    op.drop_table("export_jobs")

    op.drop_index("idx_import_templates_tenant_module", table_name="import_templates")
    op.drop_index("ix_import_templates_created_by", table_name="import_templates")
    op.drop_index("ix_import_templates_module", table_name="import_templates")
    op.drop_index("ix_import_templates_tenant_id", table_name="import_templates")
    op.drop_table("import_templates")

    op.drop_index("idx_import_jobs_module", table_name="import_jobs")
    op.drop_index("idx_import_jobs_tenant_status", table_name="import_jobs")
    op.drop_index("ix_import_jobs_created_at", table_name="import_jobs")
    op.drop_index("ix_import_jobs_created_by", table_name="import_jobs")
    op.drop_index("ix_import_jobs_status", table_name="import_jobs")
    op.drop_index("ix_import_jobs_module", table_name="import_jobs")
    op.drop_index("ix_import_jobs_tenant_id", table_name="import_jobs")
    op.drop_table("import_jobs")







