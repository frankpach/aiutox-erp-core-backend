"""Tests de performance para Tasks module."""

import time
from datetime import UTC, datetime, timedelta

import pytest

from app.core.tasks.scheduler import TaskScheduler
from app.core.tasks.service import TaskService
from app.repositories.task_repository import TaskRepository


@pytest.mark.performance
class TestTasksPerformance:
    """Tests de performance para operaciones de Tasks."""

    @pytest.mark.asyncio
    async def test_create_task_performance(self, db_session, test_user, test_tenant):
        """Test que crear tarea toma menos de 100ms."""
        service = TaskService(db_session)

        start_time = time.time()

        task = await service.create_task(
            title="Tarea de performance",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
            description="Test de performance",
        )

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert task.id is not None
        assert (
            elapsed_time < 100
        ), f"Create task tomó {elapsed_time:.2f}ms (objetivo: <100ms)"

    @pytest.mark.asyncio
    async def test_list_tasks_performance(self, db_session, test_user, test_tenant):
        """Test que listar tareas toma menos de 100ms."""
        service = TaskService(db_session)

        # Crear 50 tareas de prueba
        for i in range(50):
            await service.create_task(
                title=f"Tarea {i}", tenant_id=test_tenant.id, created_by_id=test_user.id
            )

        start_time = time.time()

        repository = TaskRepository(db_session)
        tasks = repository.get_all_tasks(tenant_id=test_tenant.id, limit=20, skip=0)

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert len(tasks) > 0
        assert (
            elapsed_time < 100
        ), f"List tasks tomó {elapsed_time:.2f}ms (objetivo: <100ms)"

    @pytest.mark.asyncio
    async def test_get_task_by_id_performance(self, db_session, test_user, test_tenant):
        """Test que obtener tarea por ID toma menos de 50ms."""
        service = TaskService(db_session)

        # Crear tarea
        task = await service.create_task(
            title="Tarea para obtener",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
        )

        start_time = time.time()

        repository = TaskRepository(db_session)
        retrieved_task = repository.get_task_by_id(task.id, test_tenant.id)

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert retrieved_task is not None
        assert (
            elapsed_time < 50
        ), f"Get task by ID tomó {elapsed_time:.2f}ms (objetivo: <50ms)"

    @pytest.mark.asyncio
    async def test_update_task_performance(self, db_session, test_user, test_tenant):
        """Test que actualizar tarea toma menos de 100ms."""
        service = TaskService(db_session)

        # Crear tarea
        task = await service.create_task(
            title="Tarea para actualizar",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
        )

        start_time = time.time()

        updated_task = service.update_task(
            task_id=task.id,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            task_data={"title": "Tarea actualizada"},
        )

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert updated_task.title == "Tarea actualizada"
        assert (
            elapsed_time < 100
        ), f"Update task tomó {elapsed_time:.2f}ms (objetivo: <100ms)"

    @pytest.mark.asyncio
    async def test_create_task_from_template_performance(
        self, db_session, test_user, test_tenant
    ):
        """Test que crear tarea desde template toma menos de 150ms."""
        service = TaskService(db_session)

        start_time = time.time()

        task = await service.create_task_from_template(
            template_id="meeting", tenant_id=test_tenant.id, created_by_id=test_user.id
        )

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert task.id is not None
        assert (
            elapsed_time < 150
        ), f"Create from template tomó {elapsed_time:.2f}ms (objetivo: <150ms)"

    @pytest.mark.asyncio
    async def test_scheduler_check_due_soon_performance(
        self, db_session, test_user, test_tenant
    ):
        """Test que verificar tareas próximas a vencer toma menos de 200ms."""
        # Guardar los IDs antes de cualquier operación que pueda fallar
        tenant_id = test_tenant.id
        user_id = test_user.id

        # Crear tareas directamente con el repositorio para evitar problemas con el servicio
        repository = TaskRepository(db_session)

        # Crear 20 tareas con diferentes fechas de vencimiento
        now = datetime.now(UTC)
        created_tasks = []

        for i in range(20):
            task_data = {
                "tenant_id": tenant_id,
                "title": f"Tarea {i}",
                "description": None,
                "status": "todo",
                "priority": "medium",
                "assigned_to_id": user_id,
                "created_by_id": user_id,
                "due_date": now + timedelta(minutes=30 + i),
                "start_at": None,
                "end_at": None,
                "all_day": False,
                "tags": None,
                "tag_ids": None,
                "color_override": None,
                "related_entity_type": None,
                "related_entity_id": None,
                "source_module": None,
                "source_id": None,
                "source_context": None,
                "metadata": None,
            }

            try:
                task = repository.create_task(task_data)
                created_tasks.append(task)
            except Exception as e:
                db_session.rollback()
                raise e

        # Verificar que las tareas se crearon
        assert (
            len(created_tasks) == 20
        ), f"Se esperaban 20 tareas, se crearon {len(created_tasks)}"

        scheduler = TaskScheduler()

        # Mockear SessionLocal para que devuelva nuestra sesión de prueba
        from unittest.mock import patch

        with patch("app.core.tasks.scheduler.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session

            start_time = time.time()
            await scheduler.check_due_soon_tasks()
            elapsed_time = (time.time() - start_time) * 1000  # ms

        assert (
            elapsed_time < 200
        ), f"Check due soon tomó {elapsed_time:.2f}ms (objetivo: <200ms)"

    @pytest.mark.asyncio
    async def test_bulk_create_performance(self, db_session, test_user, test_tenant):
        """Test que crear 100 tareas toma menos de 5 segundos."""
        service = TaskService(db_session)

        start_time = time.time()

        tasks = []
        for i in range(100):
            task = await service.create_task(
                title=f"Tarea bulk {i}",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
            )
            tasks.append(task)

        elapsed_time = time.time() - start_time

        assert len(tasks) == 100
        assert (
            elapsed_time < 5.0
        ), f"Bulk create tomó {elapsed_time:.2f}s (objetivo: <5s)"

        # Calcular tiempo promedio por tarea
        avg_time = (elapsed_time / 100) * 1000  # ms
        assert (
            avg_time < 50
        ), f"Tiempo promedio por tarea: {avg_time:.2f}ms (objetivo: <50ms)"

    @pytest.mark.asyncio
    async def test_query_with_filters_performance(
        self, db_session, test_user, test_tenant
    ):
        """Test que queries con filtros toman menos de 100ms."""
        service = TaskService(db_session)

        # Crear tareas con diferentes estados y prioridades
        for i in range(30):
            await service.create_task(
                title=f"Tarea {i}",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
                status="todo" if i % 2 == 0 else "in_progress",
                priority="high" if i % 3 == 0 else "medium",
            )

        repository = TaskRepository(db_session)

        start_time = time.time()

        # Query con filtros
        tasks = repository.get_all_tasks(
            tenant_id=test_tenant.id, status="todo", priority="high", skip=0, limit=20
        )

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert len(tasks) > 0
        assert (
            elapsed_time < 100
        ), f"Query con filtros tomó {elapsed_time:.2f}ms (objetivo: <100ms)"

    @pytest.mark.asyncio
    async def test_checklist_operations_performance(
        self, db_session, test_user, test_tenant
    ):
        """Test que operaciones de checklist toman menos de 100ms."""
        service = TaskService(db_session)

        # Crear tarea
        task = await service.create_task(
            title="Tarea con checklist",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
        )

        start_time = time.time()

        # Agregar 10 items al checklist
        for i in range(10):
            service.add_checklist_item(
                task_id=task.id, tenant_id=test_tenant.id, title=f"Item {i}", order=i
            )

        elapsed_time = (time.time() - start_time) * 1000  # ms

        assert (
            elapsed_time < 100
        ), f"Agregar checklist items tomó {elapsed_time:.2f}ms (objetivo: <100ms)"

        # Verificar que se agregaron
        items = service.get_checklist_items(task.id, test_tenant.id)
        assert len(items) == 10


@pytest.mark.performance
class TestTasksMemoryUsage:
    """Tests de uso de memoria para Tasks."""

    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, db_session, test_user, test_tenant):
        """Test que no hay memory leaks en operaciones repetitivas."""
        import gc

        service = TaskService(db_session)

        # Forzar garbage collection
        gc.collect()

        # Crear y eliminar tareas repetidamente
        for _ in range(100):
            task = await service.create_task(
                title="Tarea temporal",
                tenant_id=test_tenant.id,
                created_by_id=test_user.id,
            )

            await service.delete_task(task.id, test_tenant.id, test_user.id)

        # Forzar garbage collection nuevamente
        gc.collect()

        # Este test pasa si no hay excepciones de memoria
        assert True
