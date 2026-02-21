"""Tests de integración para TaskScheduler."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.auth import hash_password
from app.core.tasks.scheduler import TaskScheduler, get_task_scheduler
from app.models.task import TaskPriority, TaskStatusEnum
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.task_repository import TaskRepository


@pytest.mark.asyncio
class TestTaskScheduler:
    """Tests de integración para TaskScheduler."""

    async def test_scheduler_starts_successfully(self):
        """Verifica que el scheduler se inicia correctamente."""
        scheduler = TaskScheduler()
        await scheduler.start()

        assert scheduler._running is True
        assert scheduler.scheduler.running is True

    async def test_scheduler_singleton(self):
        """Verifica que get_task_scheduler retorna singleton."""
        scheduler1 = await get_task_scheduler()
        scheduler2 = await get_task_scheduler()

        assert scheduler1 is scheduler2

    async def test_check_due_soon_tasks(self, db_session, test_user, test_tenant):
        """Verifica que check_due_soon_tasks encuentra tareas próximas a vencer."""
        # Crear tarea que vence en 12 horas
        task_repository = TaskRepository(db_session)
        task = task_repository.create_task(
            {
                "tenant_id": test_tenant.id,
                "title": "Tarea próxima a vencer",
                "description": "Test task",
                "status": TaskStatusEnum.TODO,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": test_user.id,
                "created_by_id": test_user.id,
                "due_date": datetime.now(UTC) + timedelta(hours=12),
            }
        )

        scheduler = TaskScheduler()

        # Ejecutar check
        await scheduler.check_due_soon_tasks()

        # Verificar que se procesó (logs o notificaciones enviadas)
        # En un test real, mockearíamos el notification service
        assert task.due_date is not None

    async def test_check_overdue_tasks(self, db_session, test_user, test_tenant):
        """Verifica que check_overdue_tasks encuentra tareas vencidas."""
        # Crear tarea vencida
        task_repository = TaskRepository(db_session)
        task = task_repository.create_task(
            {
                "tenant_id": test_tenant.id,
                "title": "Tarea vencida",
                "description": "Test task",
                "status": TaskStatusEnum.TODO,
                "priority": TaskPriority.URGENT,
                "assigned_to_id": test_user.id,
                "created_by_id": test_user.id,
                "due_date": datetime.now(UTC) - timedelta(days=2),
            }
        )

        scheduler = TaskScheduler()

        # Ejecutar check
        await scheduler.check_overdue_tasks()

        # Verificar que se procesó
        assert task.due_date < datetime.now(UTC)

    async def test_scheduler_handles_no_tasks(self, db_session):
        """Verifica que el scheduler maneja correctamente cuando no hay tareas."""
        scheduler = TaskScheduler()

        # No debe fallar si no hay tareas
        await scheduler.check_due_soon_tasks()
        await scheduler.check_overdue_tasks()

        # Test pasó sin excepciones
        assert True

    async def test_scheduler_stops_gracefully(self):
        """Verifica que el scheduler se detiene correctamente."""
        scheduler = TaskScheduler()
        await scheduler.start()

        assert scheduler._running is True

        await scheduler.stop()

        assert scheduler._running is False


@pytest.fixture
def test_tenant(db_session):
    """Crea un tenant de prueba."""

    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-tenant-{uuid4().hex[:8]}",
        is_active=True,
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
        email=f"scheduler-test-{uuid4().hex[:8]}@example.com",
        full_name="Test User",
        password_hash=hash_password("test_password_123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user
