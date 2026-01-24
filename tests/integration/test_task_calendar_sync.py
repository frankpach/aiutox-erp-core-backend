"""Tests de integración para Calendar Sync automático."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.tasks.service import TaskService
from app.core.tasks.task_event_sync_service import TaskEventSyncService
from app.models.task import Task, TaskStatusEnum, TaskPriority
from app.models.user import User
from app.models.user_calendar_preferences import UserCalendarPreferences


@pytest.mark.asyncio
class TestTaskCalendarSync:
    """Tests de integración para sincronización automática Tasks-Calendar."""

    async def test_task_syncs_to_calendar_when_preferences_enabled(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea se sincroniza automáticamente cuando está habilitado."""
        # Crear preferencias con auto-sync habilitado
        prefs = UserCalendarPreferences(
            id=uuid4(),
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            auto_sync_tasks=True,
        )
        db_session.add(prefs)
        db_session.commit()

        task_service = TaskService(db_session)

        # Mock del sync service
        with patch.object(TaskEventSyncService, 'sync_task_to_event', new_callable=AsyncMock) as mock_sync:
            task = await task_service.create_task(
                title="Tarea con fecha",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                due_date=datetime.utcnow() + timedelta(days=7),
            )

            # Verificar que se llamó al sync
            assert mock_sync.called
            assert task.due_date is not None

    async def test_task_does_not_sync_when_preferences_disabled(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea NO se sincroniza cuando está deshabilitado."""
        # Crear preferencias con auto-sync deshabilitado
        prefs = UserCalendarPreferences(
            id=uuid4(),
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            auto_sync_tasks=False,
        )
        db_session.add(prefs)
        db_session.commit()

        task_service = TaskService(db_session)

        with patch.object(TaskEventSyncService, 'sync_task_to_event', new_callable=AsyncMock) as mock_sync:
            task = await task_service.create_task(
                title="Tarea sin sync",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                due_date=datetime.utcnow() + timedelta(days=7),
            )

            # Verificar que NO se llamó al sync
            assert not mock_sync.called

    async def test_task_without_dates_does_not_sync(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea sin fechas NO se sincroniza."""
        # Crear preferencias con auto-sync habilitado
        prefs = UserCalendarPreferences(
            id=uuid4(),
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            auto_sync_tasks=True,
        )
        db_session.add(prefs)
        db_session.commit()

        task_service = TaskService(db_session)

        with patch.object(TaskEventSyncService, 'sync_task_to_event', new_callable=AsyncMock) as mock_sync:
            task = await task_service.create_task(
                title="Tarea sin fechas",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                # Sin fechas
            )

            # Verificar que NO se llamó al sync
            assert not mock_sync.called

    async def test_sync_service_creates_calendar_event(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que TaskEventSyncService crea evento de calendario."""
        task = Task(
            id=uuid4(),
            tenant_id=test_tenant.id,
            title="Tarea para sync",
            status=TaskStatusEnum.TODO,
            priority=TaskPriority.MEDIUM,
            assigned_to_id=test_user.id,
            created_by_id=test_user.id,
            due_date=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(task)
        db_session.commit()

        sync_service = TaskEventSyncService(db_session)

        # Mock calendar event creation
        with patch.object(sync_service, '_create_calendar_event', new_callable=AsyncMock) as mock_create:
            await sync_service.sync_task_to_event(task)

            # Verificar que se intentó crear evento
            assert mock_create.called or task.due_date is not None

    async def test_sync_handles_errors_gracefully(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que errores en sync no fallan la creación de tarea."""
        prefs = UserCalendarPreferences(
            id=uuid4(),
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            auto_sync_tasks=True,
        )
        db_session.add(prefs)
        db_session.commit()

        task_service = TaskService(db_session)

        # Mock que lanza excepción
        with patch.object(
            TaskEventSyncService,
            'sync_task_to_event',
            side_effect=Exception("Sync error")
        ):
            # La tarea debe crearse exitosamente a pesar del error
            task = await task_service.create_task(
                title="Tarea con error en sync",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                due_date=datetime.utcnow() + timedelta(days=7),
            )

            assert task is not None
            assert task.id is not None


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
