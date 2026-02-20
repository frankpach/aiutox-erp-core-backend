"""Tests de integración para Task Templates."""

import pytest

from app.core.tasks.templates import get_task_template_service


@pytest.mark.asyncio
class TestTaskTemplates:
    """Tests de integración para templates de tareas."""

    async def test_create_task_from_template(self, db_session, test_user, test_tenant):
        """Verifica creación de tarea desde template."""
        template_service = get_task_template_service(db_session)

        # Usar template predefinido por su clave (no UUID)
        template_key = "meeting"  # Clave del template

        # Crear tarea desde template
        task_data = template_service.create_task_from_template(
            template_id=template_key,
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            overrides={"title": "Tarea desde template"},
        )

        assert task_data is not None
        assert task_data["title"] == "Tarea desde template"
        assert "Plantilla para crear reuniones" in task_data["description"]

    async def test_template_usage_count_increments(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que usage_count se incrementa al usar template."""
        template_service = get_task_template_service(db_session)

        # Usar template predefinido por su clave
        template_key = "meeting"  # Clave del template

        # Obtener el template para verificar usage_count inicial
        template = template_service.get_template(template_key)
        initial_count = template.usage_count

        task_data = template_service.create_task_from_template(
            template_id=template_key,
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
        )

        # Verificar que usage_count se incrementó
        assert template.usage_count == initial_count + 1
        assert task_data is not None

    async def test_get_popular_templates(self, db_session, test_user, test_tenant):
        """Verifica obtención de templates populares."""
        template_service = get_task_template_service(db_session)

        # Obtener templates populares
        popular = template_service.get_popular_templates(
            tenant_id=test_tenant.id, limit=3
        )

        assert len(popular) <= 3
        # Verificar que están ordenados por usage_count descendente
        if len(popular) > 1:
            assert popular[0].usage_count >= popular[1].usage_count
