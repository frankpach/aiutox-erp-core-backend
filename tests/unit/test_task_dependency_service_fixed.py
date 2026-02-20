"""Unit tests for Task Dependency Service."""

import pytest

from app.core.tasks.dependency_service import TaskDependencyService
from app.models.task import Task


@pytest.mark.unit
class TestTaskDependencyService:
    """Unit tests for TaskDependencyService."""

    @pytest.fixture
    def dependency_service(self, db_session):
        """Create dependency service instance."""
        return TaskDependencyService(db_session)

    @pytest.fixture
    def sample_tasks(self, db_session, test_tenant, test_user):
        """Create sample tasks for testing."""
        task1 = Task(
            tenant_id=test_tenant.id,
            title="Task 1",
            created_by_id=test_user.id,
            status="todo",
            priority="medium",
        )
        task2 = Task(
            tenant_id=test_tenant.id,
            title="Task 2",
            created_by_id=test_user.id,
            status="todo",
            priority="medium",
        )
        task3 = Task(
            tenant_id=test_tenant.id,
            title="Task 3",
            created_by_id=test_user.id,
            status="todo",
            priority="medium",
        )

        db_session.add_all([task1, task2, task3])
        db_session.commit()

        # Refresh objects to get their IDs
        db_session.refresh(task1)
        db_session.refresh(task2)
        db_session.refresh(task3)

        return task1, task2, task3

    def test_create_dependency_success(
        self, dependency_service, sample_tasks, test_tenant
    ):
        """Test successful dependency creation."""
        task1, task2, _ = sample_tasks

        dependency = dependency_service.add_dependency(
            task_id=task1.id,
            depends_on_id=task2.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )

        assert dependency.task_id == task1.id
        assert dependency.depends_on_id == task2.id
        assert dependency.dependency_type == "finish_to_start"
        assert dependency.tenant_id == test_tenant.id

    def test_get_task_dependencies(self, dependency_service, sample_tasks, test_tenant):
        """Test retrieving task dependencies."""
        task1, task2, task3 = sample_tasks

        # Create dependencies: task1 -> task2, task1 -> task3
        dep1 = dependency_service.add_dependency(
            task_id=task1.id,
            depends_on_id=task2.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )
        dep2 = dependency_service.add_dependency(
            task_id=task1.id,
            depends_on_id=task3.id,
            dependency_type="start_to_start",
            tenant_id=test_tenant.id,
        )

        dependencies = dependency_service.get_dependencies(task1.id, test_tenant.id)

        assert len(dependencies) == 2
        dependency_ids = [dep.id for dep in dependencies]
        assert dep1.id in dependency_ids
        assert dep2.id in dependency_ids

    def test_get_task_dependents(self, dependency_service, sample_tasks, test_tenant):
        """Test retrieving tasks that depend on a task."""
        task1, task2, task3 = sample_tasks

        # Create dependencies: task2 -> task1, task3 -> task1
        dependency_service.add_dependency(
            task_id=task2.id,
            depends_on_id=task1.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )
        dependency_service.add_dependency(
            task_id=task3.id,
            depends_on_id=task1.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )

        dependents = dependency_service.get_dependents(
            task_id=task1.id, tenant_id=test_tenant.id
        )

        assert len(dependents) == 2
        dependent_task_ids = [dep.task_id for dep in dependents]
        assert task2.id in dependent_task_ids
        assert task3.id in dependent_task_ids

    def test_delete_dependency_success(
        self, dependency_service, sample_tasks, test_tenant
    ):
        """Test successful dependency deletion."""
        task1, task2, _ = sample_tasks

        # Create dependency
        dependency = dependency_service.add_dependency(
            task_id=task1.id,
            depends_on_id=task2.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )

        # Delete dependency
        result = dependency_service.remove_dependency(
            dependency_id=dependency.id, tenant_id=test_tenant.id
        )

        assert result is True

        # Verify dependency is deleted
        dependencies = dependency_service.get_dependencies(
            task_id=task1.id, tenant_id=test_tenant.id
        )
        assert len(dependencies) == 0

    def test_delete_dependency_not_found(self, dependency_service, test_tenant):
        """Test deleting non-existent dependency."""
        from uuid import uuid4

        result = dependency_service.remove_dependency(
            dependency_id=uuid4(), tenant_id=test_tenant.id
        )

        assert result is False

    def test_check_circular_dependencies(
        self, dependency_service, sample_tasks, test_tenant
    ):
        """Test circular dependency detection."""
        task1, task2, task3 = sample_tasks

        # No dependencies initially
        has_cycle = dependency_service._would_create_cycle(
            task_id=task1.id, depends_on_id=task2.id
        )
        assert has_cycle is False

        # Create dependency: task1 -> task2
        dependency_service.add_dependency(
            task_id=task1.id,
            depends_on_id=task2.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )

        # Try to create circular dependency: task2 -> task1
        with pytest.raises(ValueError, match="ciclo"):
            dependency_service.add_dependency(
                task_id=task2.id,
                depends_on_id=task1.id,
                dependency_type="finish_to_start",
                tenant_id=test_tenant.id,
            )

        # Create dependency: task2 -> task3 (this should work)
        dependency_service.add_dependency(
            task_id=task2.id,
            depends_on_id=task3.id,
            dependency_type="finish_to_start",
            tenant_id=test_tenant.id,
        )

        # Now task3 -> task1 would create a cycle: task3 -> task1 -> task2 -> task3
        has_cycle = dependency_service._would_create_cycle(
            task_id=task3.id, depends_on_id=task1.id
        )
        assert has_cycle is True
