"""Integration tests to verify database structure and migrations."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from app.core.config_file import get_settings


def test_database_connection(db_session):
    """Test that database connection works."""
    # Print connection info for debugging
    settings = get_settings()
    database_url = settings.DATABASE_URL

    # Mask password in URL for security
    if "@" in database_url:
        parts = database_url.split("@")
        if ":" in parts[0]:
            protocol_user = parts[0].split("://")[0] + "://"
            user_pass = parts[0].split("://")[1]
            if ":" in user_pass:
                user = user_pass.split(":")[0]
                masked_url = f"{protocol_user}{user}:***@{parts[1]}"
            else:
                masked_url = database_url
        else:
            masked_url = database_url
    else:
        masked_url = database_url

    print(f"\n[DB CONNECTION] Database Connection Info:")
    print(f"   URL (masked): {masked_url}")
    print(f"   Host: {settings.POSTGRES_HOST}")
    print(f"   Port: {settings.POSTGRES_PORT}")
    print(f"   Database: {settings.POSTGRES_DB}")
    print(f"   User: {settings.POSTGRES_USER}")
    print(f"   Password length: {len(settings.POSTGRES_PASSWORD)}")
    print(f"   Password (first 3 chars): {settings.POSTGRES_PASSWORD[:3]}...")

    # Simple query to verify connection
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_tenants_table_exists(db_session):
    """Test that tenants table exists with correct structure."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "tenants" in tables, "tenants table should exist"

    # Check columns
    columns = {col["name"]: col for col in inspector.get_columns("tenants")}

    assert "id" in columns
    assert columns["id"]["type"].python_type.__name__ == "UUID"
    assert not columns["id"]["nullable"]

    assert "name" in columns
    assert columns["name"]["type"].length == 255
    assert not columns["name"]["nullable"]

    assert "slug" in columns
    assert columns["slug"]["type"].length == 100
    assert not columns["slug"]["nullable"]

    assert "created_at" in columns
    assert "updated_at" in columns


def test_users_table_exists(db_session):
    """Test that users table exists with correct structure."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "users" in tables, "users table should exist"

    # Check columns
    columns = {col["name"]: col for col in inspector.get_columns("users")}

    # Required fields
    assert "id" in columns
    assert "email" in columns
    assert "password_hash" in columns
    assert "tenant_id" in columns, "users table should have tenant_id (not organization_id)"
    assert "is_active" in columns

    # Extended fields (from plan.md Fase 5)
    assert "first_name" in columns
    assert "last_name" in columns
    assert "middle_name" in columns
    assert "full_name" in columns
    assert "date_of_birth" in columns
    assert "job_title" in columns
    assert "department" in columns
    assert "employee_id" in columns
    assert "preferred_language" in columns
    assert "last_login_at" in columns
    assert "email_verified_at" in columns
    assert "two_factor_enabled" in columns

    # Verify tenant_id is foreign key
    foreign_keys = inspector.get_foreign_keys("users")
    tenant_fk = [fk for fk in foreign_keys if "tenant_id" in fk["constrained_columns"]]
    assert len(tenant_fk) > 0, "users.tenant_id should be a foreign key to tenants.id"


def test_user_roles_table_exists(db_session):
    """Test that user_roles table exists with correct structure."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "user_roles" in tables, "user_roles table should exist"

    columns = {col["name"]: col for col in inspector.get_columns("user_roles")}

    assert "id" in columns
    assert "user_id" in columns
    assert "role" in columns
    assert "granted_by" in columns
    assert "created_at" in columns

    # Check unique constraint on (user_id, role)
    indexes = inspector.get_indexes("user_roles")
    unique_indexes = [idx for idx in indexes if idx.get("unique")]
    user_role_unique = [
        idx for idx in unique_indexes
        if set(idx["column_names"]) == {"user_id", "role"}
    ]
    assert len(user_role_unique) > 0, "user_roles should have unique constraint on (user_id, role)"


def test_refresh_tokens_table_exists(db_session):
    """Test that refresh_tokens table exists with correct structure."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "refresh_tokens" in tables, "refresh_tokens table should exist"

    columns = {col["name"]: col for col in inspector.get_columns("refresh_tokens")}

    assert "id" in columns
    assert "user_id" in columns
    assert "token_hash" in columns
    assert "expires_at" in columns
    assert "revoked_at" in columns
    assert "created_at" in columns

    # Check unique constraint on token_hash
    indexes = inspector.get_indexes("refresh_tokens")
    unique_indexes = [idx for idx in indexes if idx.get("unique")]
    token_hash_unique = [
        idx for idx in unique_indexes
        if "token_hash" in idx["column_names"]
    ]
    assert len(token_hash_unique) > 0, "refresh_tokens.token_hash should be unique"


def test_organizations_table_exists(db_session):
    """Test that organizations table exists (business entities, not multi-tenancy)."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "organizations" in tables, "organizations table should exist (business entities)"

    columns = {col["name"]: col for col in inspector.get_columns("organizations")}

    assert "id" in columns
    assert "tenant_id" in columns, "organizations should have tenant_id for multi-tenancy"
    assert "name" in columns
    assert "legal_name" in columns
    assert "tax_id" in columns
    assert "organization_type" in columns
    assert "is_active" in columns

    # Verify tenant_id is foreign key
    foreign_keys = inspector.get_foreign_keys("organizations")
    tenant_fk = [fk for fk in foreign_keys if "tenant_id" in fk["constrained_columns"]]
    assert len(tenant_fk) > 0, "organizations.tenant_id should be a foreign key to tenants.id"


def test_contacts_table_exists(db_session):
    """Test that contacts table exists."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "contacts" in tables, "contacts table should exist"

    columns = {col["name"]: col for col in inspector.get_columns("contacts")}

    assert "id" in columns
    assert "tenant_id" in columns
    assert "organization_id" in columns, "contacts should have organization_id (nullable)"
    assert "first_name" in columns
    assert "last_name" in columns
    assert "full_name" in columns
    assert "job_title" in columns
    assert "is_primary_contact" in columns
    assert "is_active" in columns


def test_contact_methods_table_exists(db_session):
    """Test that contact_methods table exists (polymorphic)."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "contact_methods" in tables, "contact_methods table should exist"

    columns = {col["name"]: col for col in inspector.get_columns("contact_methods")}

    assert "id" in columns
    assert "entity_type" in columns, "contact_methods should have entity_type (polymorphic)"
    assert "entity_id" in columns, "contact_methods should have entity_id (polymorphic)"
    assert "method_type" in columns
    assert "value" in columns
    assert "is_primary" in columns
    assert "is_verified" in columns

    # Check address fields (for method_type=address)
    assert "address_line1" in columns
    assert "city" in columns
    assert "country" in columns


def test_person_identifications_table_exists(db_session):
    """Test that person_identifications table exists (for future use)."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "person_identifications" in tables, "person_identifications table should exist"

    columns = {col["name"]: col for col in inspector.get_columns("person_identifications")}

    assert "id" in columns
    assert "entity_type" in columns, "person_identifications should have entity_type (polymorphic)"
    assert "entity_id" in columns, "person_identifications should have entity_id (polymorphic)"
    assert "document_type" in columns
    assert "document_number" in columns


def test_tenant_id_not_organization_id(db_session):
    """Test that users table uses tenant_id, not organization_id."""
    inspector = inspect(db_session.bind)
    columns = {col["name"]: col for col in inspector.get_columns("users")}

    assert "tenant_id" in columns, "users table should have tenant_id"
    assert "organization_id" not in columns, "users table should NOT have organization_id (renamed to tenant_id)"


def test_all_required_tables_exist(db_session):
    """Test that all required tables from the plan exist."""
    inspector = inspect(db_session.bind)
    tables = set(inspector.get_table_names())

    required_tables = {
        "tenants",  # Multi-tenancy
        "users",  # Users with auth
        "user_roles",  # Global roles
        "refresh_tokens",  # Refresh tokens
        "organizations",  # Business entities
        "contacts",  # Person contacts
        "contact_methods",  # Polymorphic contact methods
        "person_identifications",  # Future use
    }

    missing_tables = required_tables - tables
    assert not missing_tables, f"Missing required tables: {missing_tables}"


def test_alembic_version_table_exists(db_session):
    """Test that alembic_version table exists (migration tracking)."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "alembic_version" in tables, "alembic_version table should exist for migration tracking"


def test_foreign_key_constraints(db_session):
    """Test that foreign key constraints are properly set up."""
    inspector = inspect(db_session.bind)

    # Users -> Tenants
    users_fks = inspector.get_foreign_keys("users")
    users_tenant_fk = [fk for fk in users_fks if "tenant_id" in fk["constrained_columns"]]
    assert len(users_tenant_fk) > 0, "users should have FK to tenants.id"
    assert users_tenant_fk[0]["referred_table"] == "tenants"

    # Organizations -> Tenants
    orgs_fks = inspector.get_foreign_keys("organizations")
    orgs_tenant_fk = [fk for fk in orgs_fks if "tenant_id" in fk["constrained_columns"]]
    assert len(orgs_tenant_fk) > 0, "organizations should have FK to tenants.id"

    # Contacts -> Tenants and Organizations
    contacts_fks = inspector.get_foreign_keys("contacts")
    contacts_tenant_fk = [fk for fk in contacts_fks if "tenant_id" in fk["constrained_columns"]]
    contacts_org_fk = [fk for fk in contacts_fks if "organization_id" in fk["constrained_columns"]]
    assert len(contacts_tenant_fk) > 0, "contacts should have FK to tenants.id"
    assert len(contacts_org_fk) > 0, "contacts should have FK to organizations.id"

    # UserRoles -> Users
    user_roles_fks = inspector.get_foreign_keys("user_roles")
    user_roles_user_fk = [fk for fk in user_roles_fks if "user_id" in fk["constrained_columns"]]
    assert len(user_roles_user_fk) > 0, "user_roles should have FK to users.id"

    # RefreshTokens -> Users
    refresh_tokens_fks = inspector.get_foreign_keys("refresh_tokens")
    refresh_tokens_user_fk = [fk for fk in refresh_tokens_fks if "user_id" in fk["constrained_columns"]]
    assert len(refresh_tokens_user_fk) > 0, "refresh_tokens should have FK to users.id"



