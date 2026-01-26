"""Tests de integración para TaskNotificationService."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.tasks.notification_service import TaskNotificationService
from app.models.task import Task, TaskPriority, TaskStatusEnum
from app.models.user import User


@pytest.mark.asyncio
class TestTaskNotificationService:
    """Tests de integración para notificaciones de tareas."""

    async def test_notify_task_created(self, db_session, test_user, test_task):
        """Verifica notificación cuando se crea una tarea."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_created(test_task, test_user)

            # Debe enviar notificación al usuario asignado
            assert mock_send.called

    async def test_notify_task_assigned(self, db_session, test_user, test_task, another_user):
        """Verifica notificación cuando se asigna una tarea."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_assigned(test_task, another_user, test_user)

            # Debe enviar al menos una notificación
            assert mock_send.call_count >= 1

            # Verificar que se notificó al usuario asignado
            calls = mock_send.call_args_list
            user_ids = [call.kwargs['user_id'] for call in calls]
            assert another_user.id in user_ids

    async def test_notify_task_unassigned(self, db_session, test_user, test_task, another_user):
        """Verifica notificación cuando se desasigna una tarea."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_unassigned(test_task, another_user, test_user)

            # Debe enviar notificación al usuario desasignado
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'task_unassigned'

    async def test_notify_task_status_changed(self, db_session, test_user, test_task):
        """Verifica notificación cuando cambia el estado de una tarea."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_status_changed(
                test_task,
                old_status='todo',
                new_status='in_progress',
                changed_by=test_user
            )

            # Debe enviar notificación
            assert mock_send.called

    async def test_notify_task_due_soon(self, db_session, test_user):
        """Verifica notificación para tareas próximas a vencer."""
        # Crear tarea que vence en 12 horas
        task = Task(
            id=uuid4(),
            tenant_id=test_user.tenant_id,
            title="Tarea próxima a vencer",
            status=TaskStatusEnum.TODO,
            priority=TaskPriority.HIGH,
            assigned_to_id=test_user.id,
            created_by_id=test_user.id,
            due_date=datetime.utcnow() + timedelta(hours=12)
        )

        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_due_soon(task)

            # Debe enviar notificación
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'task_due_soon'

    async def test_notify_task_overdue(self, db_session, test_user):
        """Verifica notificación para tareas vencidas."""
        # Crear tarea vencida
        task = Task(
            id=uuid4(),
            tenant_id=test_user.tenant_id,
            title="Tarea vencida",
            status=TaskStatusEnum.TODO,
            priority=TaskPriority.URGENT,
            assigned_to_id=test_user.id,
            created_by_id=test_user.id,
            due_date=datetime.utcnow() - timedelta(days=2)
        )

        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_task_overdue(task)

            # Debe enviar notificación
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'task_overdue'

    async def test_notify_comment_added(self, db_session, test_user, test_task, another_user):
        """Verifica notificación cuando se agrega un comentario."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_comment_added(
                test_task,
                comment_text="Este es un comentario de prueba",
                commented_by=another_user
            )

            # Debe enviar notificación
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'task_comment_added'

    async def test_notify_file_attached(self, db_session, test_user, test_task, another_user):
        """Verifica notificación cuando se adjunta un archivo."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_file_attached(
                test_task,
                filename="documento.pdf",
                attached_by=another_user
            )

            # Debe enviar notificación
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'task_file_attached'

    async def test_notify_checklist_updated(self, db_session, test_user, test_task, another_user):
        """Verifica notificación cuando se actualiza el checklist."""
        notification_service = TaskNotificationService(db_session)

        with patch.object(notification_service, '_send_notification', new_callable=AsyncMock) as mock_send:
            await notification_service.notify_checklist_updated(
                test_task,
                updated_by=another_user,
                item_text="Item de prueba",
                completed=True
            )

            # Debe enviar notificación
            assert mock_send.called

            # Verificar tipo de notificación
            first_call = mock_send.call_args_list[0]
            assert first_call.kwargs['type'] == 'checklist_updated'

    async def test_notification_service_fallback(self):
        """Verifica que el servicio funciona sin NotificationService."""
        # Sin db_session para forzar fallback
        notification_service = TaskNotificationService(db=None)

        assert notification_service.is_connected is False
        assert notification_service.notification_service is None


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


@pytest.fixture
def another_user(db_session, test_tenant):
    """Crea otro usuario de prueba."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="another@example.com",
        full_name="Another User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_task(db_session, test_user):
    """Crea una tarea de prueba."""
    task = Task(
        id=uuid4(),
        tenant_id=test_user.tenant_id,
        title="Tarea de prueba",
        description="Descripción de prueba",
        status=TaskStatusEnum.TODO,
        priority=TaskPriority.MEDIUM,
        assigned_to_id=test_user.id,
        created_by_id=test_user.id,
        due_date=datetime.utcnow() + timedelta(days=7)
    )
    db_session.add(task)
    db_session.commit()
    return task
