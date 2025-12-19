"""Unit tests for ViewService."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.views.service import ViewService
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = MagicMock()
    return publisher


@pytest.fixture
def view_service(db_session, mock_event_publisher):
    """Create ViewService instance."""
    return ViewService(db=db_session, event_publisher=mock_event_publisher)


def test_create_saved_filter(view_service, test_user, test_tenant):
    """Test creating a saved filter."""
    filter_obj = view_service.create_saved_filter(
        filter_data={
            "name": "Test Filter",
            "module": "products",
            "filters": {"status": "active"},
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert filter_obj.name == "Test Filter"
    assert filter_obj.module == "products"
    assert filter_obj.tenant_id == test_tenant.id
    assert filter_obj.created_by == test_user.id


def test_create_custom_view(view_service, test_user, test_tenant):
    """Test creating a custom view."""
    view = view_service.create_custom_view(
        view_data={
            "name": "Test View",
            "module": "products",
            "columns": {"name": True, "price": True},
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert view.name == "Test View"
    assert view.module == "products"
    assert view.tenant_id == test_tenant.id
    assert view.created_by == test_user.id


def test_get_saved_filters(view_service, test_user, test_tenant):
    """Test getting saved filters."""
    # Create multiple filters
    filter1 = view_service.create_saved_filter(
        filter_data={
            "name": "Filter 1",
            "module": "products",
            "filters": {"status": "active"},
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    filters = view_service.get_saved_filters(
        tenant_id=test_tenant.id,
        module="products",
        user_id=test_user.id,
    )

    assert len(filters) >= 1
    assert any(f.id == filter1.id for f in filters)








