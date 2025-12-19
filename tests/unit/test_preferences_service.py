"""Unit tests for PreferencesService."""

import pytest
from uuid import uuid4

from app.core.preferences.service import PreferencesService
from app.repositories.preference_repository import PreferenceRepository


@pytest.fixture
def preferences_service(db_session):
    """Create PreferencesService instance."""
    return PreferencesService(db_session)


def test_set_and_get_preference(preferences_service, test_user, test_tenant):
    """Test setting and getting a preference."""
    # Set preference
    result = preferences_service.set_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="basic",
        key="language",
        value="en",
    )
    assert result["key"] == "language"
    assert result["value"] == "en"

    # Get preference
    value = preferences_service.get_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="basic",
        key="language",
    )
    assert value == "en"


def test_get_preference_with_default(preferences_service, test_user, test_tenant):
    """Test getting a preference with default value."""
    value = preferences_service.get_preference(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        preference_type="basic",
        key="nonexistent",
        default="default_value",
    )
    assert value == "default_value"


def test_set_org_preference(preferences_service, test_tenant):
    """Test setting an organization preference."""
    result = preferences_service.set_org_preference(
        tenant_id=test_tenant.id,
        preference_type="basic",
        key="default_language",
        value="es",
    )
    assert result["key"] == "default_language"
    assert result["value"] == "es"










