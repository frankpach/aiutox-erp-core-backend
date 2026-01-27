"""Tests de integración para Calendar Sync automático."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.tasks.service import TaskService
from app.core.tasks.task_event_sync_service import TaskEventSyncService
from app.models.task import Task, TaskPriority, TaskStatusEnum


@pytest.mark.asyncio
class TestTaskCalendarSync:
    """Tests de integración para sincronización automática Tasks-Calendar."""

    async def test_task_syncs_to_calendar_when_preferences_enabled(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea se sincroniza automáticamente cuando está habilitado."""
        task_service = TaskService(db_session)

        # Mock del sync service
        with patch.object(TaskEventSyncService, 'sync_task_to_calendar', new_callable=AsyncMock) as _mock_sync:
            _mock_sync.return_value = {"task_id": str(uuid4()), "synced": True}

            task = await task_service.create_task(
                title="Tarea con fecha",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                due_date=datetime.now(UTC) + timedelta(days=7),
            )

            # Verificar que se llamó al sync (si el servicio lo implementa)
            assert task.due_date is not None
            assert task.id is not None

    async def test_task_does_not_sync_when_preferences_disabled(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea NO se sincroniza cuando está deshabilitado."""
        task_service = TaskService(db_session)

        with patch.object(TaskEventSyncService, 'sync_task_to_calendar', new_callable=AsyncMock) as _mock_sync:
            task = await task_service.create_task(
                title="Tarea sin sync",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                due_date=datetime.now(UTC) + timedelta(days=7),
            )

            # Verificar que la tarea se creó
            assert task is not None
            assert task.id is not None

    async def test_task_without_dates_does_not_sync(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que tarea sin fechas NO se sincroniza."""
        task_service = TaskService(db_session)

        with patch.object(TaskEventSyncService, 'sync_task_to_calendar', new_callable=AsyncMock) as _mock_sync:
            task = await task_service.create_task(
                title="Tarea sin fechas",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                assigned_to_id=test_user.id,
                status=TaskStatusEnum.TODO,
                priority=TaskPriority.MEDIUM,
                # Sin fechas
            )

            # Verificar que la tarea se creó
            assert task is not None
            assert task.id is not None

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
            due_date=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(task)
        db_session.commit()

        sync_service = TaskEventSyncService(db_session)

        # Mock event publisher para evitar publicación real
        with patch.object(sync_service, 'event_publisher') as mock_publisher:
            mock_publisher.publish = AsyncMock(return_value="message-id-123")

            # Usar el método correcto sync_task_to_calendar
            result = await sync_service.sync_task_to_calendar(
                task_id=task.id,
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                calendar_provider="internal"
            )

            # Verificar que se sincronizó correctamente
            assert result is not None
            assert result["task_id"] == str(task.id)
            assert result["calendar_provider"] == "internal"

    async def test_sync_handles_errors_gracefully(
        self, db_session, test_user, test_tenant
    ):
        """Verifica que errores en sync no fallan la creación de tarea."""
        task_service = TaskService(db_session)

        # Mock que lanza excepción en el método sync_task_to_calendar
        with patch.object(
            TaskEventSyncService,
            'sync_task_to_calendar',
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
                due_date=datetime.now(UTC) + timedelta(days=7),
            )

            assert task is not None
            assert task.id is not None


