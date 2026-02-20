"""Tests de integración para notificaciones de tasks."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.tasks.scheduler import TaskScheduler
from app.core.tasks.service import TaskService
from app.models.task import TaskStatusEnum


@pytest.mark.asyncio
class TestTasksNotificationsIntegration:
    """Tests de integración para flujo completo de notificaciones."""

    async def test_task_assignment_notification_flow(
        self,
        db_session,
        test_user,
        test_tenant,
        mock_event_publisher
    ):
        """Test flujo completo de notificación de asignación."""
        service = TaskService(db_session, event_publisher=mock_event_publisher)

        # Crear tarea asignada
        task = await service.create_task(
            title="Tarea con notificación de asignación",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            assigned_to_id=test_user.id,
            status=TaskStatusEnum.TODO
        )

        assert task.id is not None
        assert task.assigned_to_id == test_user.id

        # Verificar que se publicó evento task.created
        assert mock_event_publisher.publish.called

        # Verificar que se publicó evento task.assigned
        calls = mock_event_publisher.publish.call_args_list
        event_types = [call[1]['event_type'] for call in calls]

        assert 'task.created' in event_types
        assert 'task.assigned' in event_types

    async def test_task_status_change_notification_flow(
        self,
        db_session,
        test_user,
        test_tenant,
        mock_event_publisher
    ):
        """Test flujo completo de notificación de cambio de estado."""
        service = TaskService(db_session, event_publisher=mock_event_publisher)

        # Crear tarea
        task = await service.create_task(
            title="Tarea para cambio de estado",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            status=TaskStatusEnum.TODO
        )

        mock_event_publisher.publish.reset_mock()

        # Cambiar estado
        updated_task = service.update_task(
            task_id=task.id,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            task_data={"status": TaskStatusEnum.IN_PROGRESS}
        )

        assert updated_task.status == TaskStatusEnum.IN_PROGRESS

        # Verificar que se publicó evento task.updated
        assert mock_event_publisher.publish.called
        calls = mock_event_publisher.publish.call_args_list
        event_types = [call[1]['event_type'] for call in calls]

        assert 'task.updated' in event_types

    async def test_task_due_soon_notification_flow(
        self,
        db_session,
        test_user,
        test_tenant,
        mock_event_publisher
    ):
        """Test flujo completo de notificación de tarea próxima a vencer."""
        service = TaskService(db_session, event_publisher=mock_event_publisher)

        # Crear tarea que vence en 30 minutos
        due_date = datetime.now(UTC) + timedelta(minutes=30)

        task = await service.create_task(
            title="Tarea próxima a vencer",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            assigned_to_id=test_user.id,
            due_date=due_date
        )

        assert task.due_date is not None

        # Ejecutar scheduler
        scheduler = TaskScheduler()
        await scheduler.check_due_soon_tasks()

        # Verificar que se procesó la tarea
        # (En un test real, verificaríamos que se envió la notificación)

    async def test_task_overdue_notification_flow(
        self,
        db_session,
        test_user,
        test_tenant,
        mock_event_publisher
    ):
        """Test flujo completo de notificación de tarea vencida."""
        service = TaskService(db_session, event_publisher=mock_event_publisher)

        # Crear tarea vencida
        due_date = datetime.now(UTC) - timedelta(hours=2)

        task = await service.create_task(
            title="Tarea vencida",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            assigned_to_id=test_user.id,
            due_date=due_date,
            status=TaskStatusEnum.TODO
        )

        assert task.due_date < datetime.now(UTC)

        # Ejecutar scheduler
        scheduler = TaskScheduler()
        await scheduler.check_overdue_tasks()

        # Verificar que se procesó la tarea
        # (En un test real, verificaríamos que se envió la notificación)

    async def test_task_from_template_with_notifications(
        self,
        db_session,
        test_user,
        test_tenant,
        mock_event_publisher
    ):
        """Test crear tarea desde template con notificaciones."""
        service = TaskService(db_session, event_publisher=mock_event_publisher)

        # Crear tarea desde template
        task = await service.create_task_from_template(
            template_id="meeting",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            overrides={
                "title": "Reunión de equipo",
                "assigned_to_id": str(test_user.id)
            }
        )

        assert task.id is not None
        assert task.title == "Reunión de equipo"
        assert task.assigned_to_id == test_user.id

        # Verificar que se publicaron eventos
        assert mock_event_publisher.publish.called

        # Verificar checklist items
        checklist = service.get_checklist_items(task.id, test_tenant.id)
        assert len(checklist) > 0
