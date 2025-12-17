"""Unit tests for TemplateService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.templates.service import TemplateService, TemplateRenderer
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def template_renderer():
    """Create TemplateRenderer instance."""
    return TemplateRenderer()


@pytest.fixture
def template_service(db_session, mock_event_publisher):
    """Create TemplateService instance."""
    return TemplateService(db=db_session, event_publisher=mock_event_publisher)


def test_render_template(template_renderer):
    """Test rendering a template."""
    template_content = "Hello {{ name }}!"
    variables = {"name": "World"}

    rendered = template_renderer.render(template_content, variables)

    assert rendered == "Hello World!"


def test_create_template(template_service, test_user, test_tenant, mock_event_publisher):
    """Test creating a template."""
    template = template_service.create_template(
        template_data={
            "name": "Test Template",
            "template_type": "email",
            "template_format": "html",
            "content": "Hello {{ name }}!",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert template.name == "Test Template"
    assert template.template_type == "email"
    assert template.content == "Hello {{ name }}!"
    assert template.tenant_id == test_tenant.id

    # Verify event was published
    assert mock_event_publisher.publish.called

    # Verify initial version was created
    versions = template_service.get_template_versions(template.id, test_tenant.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].is_current == True


def test_render_template_with_variables(template_service, test_user, test_tenant):
    """Test rendering a template with variables."""
    template = template_service.create_template(
        template_data={
            "name": "Test Template",
            "template_type": "email",
            "template_format": "html",
            "content": "Hello {{ name }}, your order {{ order_id }} is ready!",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    result = template_service.render_template(
        template_id=template.id,
        tenant_id=test_tenant.id,
        variables={"name": "John", "order_id": "12345"},
    )

    assert "rendered_content" in result
    assert "Hello John, your order 12345 is ready!" in result["rendered_content"]
    assert result["format"] == "html"







