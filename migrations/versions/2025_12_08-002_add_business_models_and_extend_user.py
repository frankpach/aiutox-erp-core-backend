
"""Add business models and extend user

Revision ID: 002_add_business_models_and_extend_user
Revises: 001_rename_organizations_to_tenants
Create Date: 2025-12-08 15:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_business_models"
down_revision: str | None = "001_rename_orgs_to_tenants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create organizations table (business entities)
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("organization_type", sa.String(50), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_organizations_tenant_id"), "organizations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_organizations_tax_id"), "organizations", ["tax_id"], unique=False)
    op.create_index(op.f("ix_organizations_organization_type"), "organizations", ["organization_type"], unique=False)
    op.create_index("ix_organizations_tenant_type", "organizations", ["tenant_id", "organization_type"], unique=False)
    op.create_unique_constraint("uq_organizations_tenant_tax_id", "organizations", ["tenant_id", "tax_id"])

    # Create contacts table
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("middle_name", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("is_primary_contact", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_contacts_tenant_id"), "contacts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_contacts_organization_id"), "contacts", ["organization_id"], unique=False)
    op.create_index("ix_contacts_tenant_organization", "contacts", ["tenant_id", "organization_id"], unique=False)

    # Create contact_methods table (polymorphic)
    op.create_table(
        "contact_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_type", sa.String(50), nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state_province", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_contact_methods_entity", "contact_methods", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_contact_methods_entity_type"), "contact_methods", ["entity_type"], unique=False)
    op.create_index(op.f("ix_contact_methods_entity_id"), "contact_methods", ["entity_id"], unique=False)
    op.create_unique_constraint(
        "uq_contact_methods_entity_type_value",
        "contact_methods",
        ["entity_type", "entity_id", "method_type", "value"],
    )

    # Create person_identifications table (polymorphic, for future use)
    op.create_table(
        "person_identifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("social_security_number", sa.String(100), nullable=True),
        sa.Column("issuing_country", sa.String(2), nullable=True),
        sa.Column("issuing_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expiration_date", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("issuing_authority", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_person_identifications_entity", "person_identifications", ["entity_type", "entity_id"], unique=False)
    op.create_index(op.f("ix_person_identifications_entity_type"), "person_identifications", ["entity_type"], unique=False)
    op.create_index(op.f("ix_person_identifications_entity_id"), "person_identifications", ["entity_id"], unique=False)
    op.create_index(op.f("ix_person_identifications_document_number"), "person_identifications", ["document_number"], unique=False)
    op.create_unique_constraint(
        "uq_person_identifications_entity_document",
        "person_identifications",
        ["entity_type", "entity_id", "document_type", "document_number"],
    )

    # Add new columns to users table
    op.add_column("users", sa.Column("first_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("middle_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("nationality", sa.String(2), nullable=True))
    op.add_column("users", sa.Column("marital_status", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("employee_id", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("preferred_language", sa.String(10), server_default="es", nullable=False))
    op.add_column("users", sa.Column("timezone", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("phone_verified_at", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # Create unique index for employee_id
    op.create_index(op.f("ix_users_employee_id"), "users", ["employee_id"], unique=True)


def downgrade() -> None:
    # Remove columns from users
    op.drop_index(op.f("ix_users_employee_id"), table_name="users")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "notes")
    op.drop_column("users", "bio")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "timezone")
    op.drop_column("users", "preferred_language")
    op.drop_column("users", "employee_id")
    op.drop_column("users", "department")
    op.drop_column("users", "job_title")
    op.drop_column("users", "marital_status")
    op.drop_column("users", "nationality")
    op.drop_column("users", "gender")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "middle_name")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

    # Drop person_identifications table
    op.drop_constraint("uq_person_identifications_entity_document", "person_identifications", type_="unique")
    op.drop_index(op.f("ix_person_identifications_document_number"), table_name="person_identifications")
    op.drop_index(op.f("ix_person_identifications_entity_id"), table_name="person_identifications")
    op.drop_index(op.f("ix_person_identifications_entity_type"), table_name="person_identifications")
    op.drop_index("ix_person_identifications_entity", table_name="person_identifications")
    op.drop_table("person_identifications")

    # Drop contact_methods table
    op.drop_constraint("uq_contact_methods_entity_type_value", "contact_methods", type_="unique")
    op.drop_index(op.f("ix_contact_methods_entity_id"), table_name="contact_methods")
    op.drop_index(op.f("ix_contact_methods_entity_type"), table_name="contact_methods")
    op.drop_index("ix_contact_methods_entity", table_name="contact_methods")
    op.drop_table("contact_methods")

    # Drop contacts table
    op.drop_index("ix_contacts_tenant_organization", table_name="contacts")
    op.drop_index(op.f("ix_contacts_organization_id"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_tenant_id"), table_name="contacts")
    op.drop_table("contacts")

    # Drop organizations table
    op.drop_constraint("uq_organizations_tenant_tax_id", "organizations", type_="unique")
    op.drop_index("ix_organizations_tenant_type", table_name="organizations")
    op.drop_index(op.f("ix_organizations_organization_type"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_tax_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_tenant_id"), table_name="organizations")
    op.drop_table("organizations")
