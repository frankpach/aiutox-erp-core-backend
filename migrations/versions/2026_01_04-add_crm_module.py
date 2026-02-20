"""Add CRM module tables: crm_pipelines, crm_leads, crm_opportunities

Revision ID: add_crm_module
Revises: add_inventory_module
Create Date: 2026-01-04 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_crm_module"
down_revision: str | None = "add_inventory_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crm_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_crm_pipelines_tenant_name"),
    )
    op.create_index("ix_crm_pipelines_tenant_id", "crm_pipelines", ["tenant_id"], unique=False)
    op.create_index("idx_crm_pipelines_tenant_name", "crm_pipelines", ["tenant_id", "name"], unique=False)

    op.create_table(
        "crm_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("probability", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("next_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["crm_pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_leads_tenant_id", "crm_leads", ["tenant_id"], unique=False)
    op.create_index("ix_crm_leads_pipeline_id", "crm_leads", ["pipeline_id"], unique=False)
    op.create_index("ix_crm_leads_organization_id", "crm_leads", ["organization_id"], unique=False)
    op.create_index("ix_crm_leads_contact_id", "crm_leads", ["contact_id"], unique=False)
    op.create_index("ix_crm_leads_status", "crm_leads", ["status"], unique=False)
    op.create_index("idx_crm_leads_tenant_status", "crm_leads", ["tenant_id", "status"], unique=False)

    op.create_table(
        "crm_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("probability", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("expected_close_date", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("next_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["crm_pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_opportunities_tenant_id", "crm_opportunities", ["tenant_id"], unique=False)
    op.create_index("ix_crm_opportunities_pipeline_id", "crm_opportunities", ["pipeline_id"], unique=False)
    op.create_index("ix_crm_opportunities_organization_id", "crm_opportunities", ["organization_id"], unique=False)
    op.create_index("ix_crm_opportunities_contact_id", "crm_opportunities", ["contact_id"], unique=False)
    op.create_index("ix_crm_opportunities_status", "crm_opportunities", ["status"], unique=False)
    op.create_index(
        "idx_crm_opportunities_tenant_status",
        "crm_opportunities",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_crm_opportunities_tenant_status", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_status", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_contact_id", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_organization_id", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_pipeline_id", table_name="crm_opportunities")
    op.drop_index("ix_crm_opportunities_tenant_id", table_name="crm_opportunities")
    op.drop_table("crm_opportunities")

    op.drop_index("idx_crm_leads_tenant_status", table_name="crm_leads")
    op.drop_index("ix_crm_leads_status", table_name="crm_leads")
    op.drop_index("ix_crm_leads_contact_id", table_name="crm_leads")
    op.drop_index("ix_crm_leads_organization_id", table_name="crm_leads")
    op.drop_index("ix_crm_leads_pipeline_id", table_name="crm_leads")
    op.drop_index("ix_crm_leads_tenant_id", table_name="crm_leads")
    op.drop_table("crm_leads")

    op.drop_index("idx_crm_pipelines_tenant_name", table_name="crm_pipelines")
    op.drop_index("ix_crm_pipelines_tenant_id", table_name="crm_pipelines")
    op.drop_table("crm_pipelines")
