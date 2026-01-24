"""Tests de integración para Task Templates."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.core.tasks.templates import get_task_template_service
from app.models.task_template import TaskTemplate
from app.models.user import User


@pytest.mark.asyncio
class TestTaskTemplates:
    """Tests de integración para templates de tareas."""

    async def test_create_task_from_template(self, db_session, test_user, test_tenant):
        """Verifica creación de tarea desde template."""
        # Crear template
        template = TaskTemplate(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Template de prueba",
            description="Descripción del template",
            category="testing",
            estimated_hours=2,
            created_by_id=test_user.id,
        )
        db_session.add(template)
        db_session.commit()

        template_service = get_task_template_service(db_session)

        # Crear tarea desde template
        task = await template_service.create_task_from_template(
            tenant_id=test_tenant.id,
            template_id=template.id,
            created_by_id=test_user.id,
            title="Tarea desde template",
        )

        assert task is not None
        assert task.title == "Tarea desde template"
        assert task.description == template.description

    async def test_template_usage_count_increments(self, db_session, test_user, test_tenant):
        """Verifica que usage_count se incrementa al usar template."""
        template = TaskTemplate(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Template contador",
            description="Test",
            usage_count=0,
            created_by_id=test_user.id,
        )
        db_session.add(template)
        db_session.commit()

        initial_count = template.usage_count

        template_service = get_task_template_service(db_session)
        await template_service.create_task_from_template(
            tenant_id=test_tenant.id,
            template_id=template.id,
            created_by_id=test_user.id,
        )

        db_session.refresh(template)
        assert template.usage_count == initial_count + 1

    async def test_get_popular_templates(self, db_session, test_user, test_tenant):
        """Verifica obtención de templates populares."""
        # Crear templates con diferentes usage_count
        templates = [
            TaskTemplate(
                id=uuid4(),
                tenant_id=test_tenant.id,
                name=f"Template {i}",
                description="Test",
                usage_count=i * 10,
                created_by_id=test_user.id,
            )
            for i in range(5)
        ]
        for template in templates:
            db_session.add(template)
        db_session.commit()

        template_service = get_task_template_service(db_session)
        popular = template_service.get_popular_templates(
            tenant_id=test_tenant.id,
            limit=3
        )

        assert len(popular) <= 3
        # Verificar que están ordenados por usage_count descendente
        if len(popular) > 1:
            assert popular[0].usage_count >= popular[1].usage_count


@pytest.fixture
def test_tenant(db_session):
    """Crea un tenant de prueba."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def test_user(db_session, test_tenant):
    """Crea un usuario de prueba."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="test@example.com",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user
