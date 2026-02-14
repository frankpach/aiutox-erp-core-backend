"""Unit tests for GamificationEventHandler."""

from uuid import uuid4

import pytest

from app.core.gamification.points_service import PointsService
from app.modules.gamification.event_handlers import (
    DEFAULT_POINTS_CONFIG,
    ON_TIME_BONUS,
    PRIORITY_BONUS,
    GamificationEventHandler,
)


@pytest.fixture
def handler(db_session, test_tenant):
    """Create GamificationEventHandler instance."""
    return GamificationEventHandler(db=db_session, tenant_id=test_tenant.id)


@pytest.fixture
def points_service(db_session, test_tenant):
    """Create PointsService for verifying results."""
    return PointsService(db=db_session, tenant_id=test_tenant.id)


class TestHandleTaskCompleted:
    """Tests para handle_task_completed."""

    def test_awards_base_points(self, handler, points_service, test_user):
        """Otorga puntos base por completar tarea."""
        task_id = uuid4()
        handler.handle_task_completed(
            user_id=test_user.id,
            task_id=task_id,
            metadata={"priority": "medium"},
        )

        user_points = points_service.get_user_points(test_user.id)
        assert user_points is not None
        expected = DEFAULT_POINTS_CONFIG["tasks"]["task.completed"]
        assert user_points.total_points >= expected

    def test_priority_bonus_urgent(self, handler, points_service, test_user):
        """Tarea urgente otorga bonus de prioridad."""
        handler.handle_task_completed(
            user_id=test_user.id,
            task_id=uuid4(),
            metadata={"priority": "urgent"},
        )

        user_points = points_service.get_user_points(test_user.id)
        base = DEFAULT_POINTS_CONFIG["tasks"]["task.completed"]
        expected_min = base + PRIORITY_BONUS["urgent"]
        assert user_points.total_points >= expected_min

    def test_on_time_bonus(self, handler, points_service, test_user):
        """Completar a tiempo otorga bonus."""
        handler.handle_task_completed(
            user_id=test_user.id,
            task_id=uuid4(),
            metadata={"priority": "medium", "completed_on_time": True},
        )

        user_points = points_service.get_user_points(test_user.id)
        base = DEFAULT_POINTS_CONFIG["tasks"]["task.completed"]
        expected_min = base + ON_TIME_BONUS
        assert user_points.total_points >= expected_min

    def test_idempotency(self, handler, points_service, test_user):
        """El mismo evento no se procesa dos veces."""
        task_id = uuid4()

        handler.handle_task_completed(
            user_id=test_user.id,
            task_id=task_id,
            metadata={"priority": "medium"},
        )
        points_after_first = points_service.get_user_points(test_user.id).total_points

        handler.handle_task_completed(
            user_id=test_user.id,
            task_id=task_id,
            metadata={"priority": "medium"},
        )
        points_after_second = points_service.get_user_points(test_user.id).total_points

        assert points_after_first == points_after_second


class TestHandleTaskCreated:
    """Tests para handle_task_created."""

    def test_awards_points_for_creation(self, handler, points_service, test_user):
        """Otorga puntos por crear tarea."""
        handler.handle_task_created(
            user_id=test_user.id,
            task_id=uuid4(),
        )

        user_points = points_service.get_user_points(test_user.id)
        assert user_points is not None
        assert user_points.total_points > 0

    def test_idempotency(self, handler, points_service, test_user):
        """El mismo evento no se procesa dos veces."""
        task_id = uuid4()

        handler.handle_task_created(user_id=test_user.id, task_id=task_id)
        points_1 = points_service.get_user_points(test_user.id).total_points

        handler.handle_task_created(user_id=test_user.id, task_id=task_id)
        points_2 = points_service.get_user_points(test_user.id).total_points

        assert points_1 == points_2


class TestHandleEventAttended:
    """Tests para handle_event_attended."""

    def test_awards_points_for_attendance(self, handler, points_service, test_user):
        """Otorga puntos por asistir a evento de calendario."""
        handler.handle_event_attended(
            user_id=test_user.id,
            event_id=uuid4(),
        )

        user_points = points_service.get_user_points(test_user.id)
        assert user_points is not None
        expected = DEFAULT_POINTS_CONFIG["calendar"]["calendar.event_attended"]
        assert user_points.total_points >= expected

    def test_idempotency(self, handler, points_service, test_user):
        """El mismo evento no se procesa dos veces."""
        event_id = uuid4()

        handler.handle_event_attended(user_id=test_user.id, event_id=event_id)
        points_1 = points_service.get_user_points(test_user.id).total_points

        handler.handle_event_attended(user_id=test_user.id, event_id=event_id)
        points_2 = points_service.get_user_points(test_user.id).total_points

        assert points_1 == points_2


class TestCalculatePoints:
    """Tests para _calculate_points."""

    def test_base_points_from_config(self, handler):
        """Usa puntos base de la configuración."""
        points = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "medium"},
        )
        assert points == DEFAULT_POINTS_CONFIG["tasks"]["task.completed"]

    def test_unknown_event_defaults_to_10(self, handler):
        """Evento desconocido usa 10 puntos por defecto."""
        points = handler._calculate_points(
            event_type="unknown.event",
            source_module="unknown",
            metadata={"priority": "medium"},
        )
        assert points == 10

    def test_priority_bonus_applied(self, handler):
        """Bonus de prioridad se aplica correctamente."""
        points_high = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "high"},
        )
        points_low = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "low"},
        )
        assert points_high > points_low

    def test_on_time_bonus_applied(self, handler):
        """Bonus por completar a tiempo se aplica."""
        points_on_time = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "medium", "completed_on_time": True},
        )
        points_late = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "medium", "completed_on_time": False},
        )
        assert points_on_time - points_late == ON_TIME_BONUS


class TestCustomConfig:
    """Tests para configuración personalizada."""

    def test_custom_points_config(self, db_session, test_tenant, test_user):
        """Acepta configuración de puntos personalizada."""
        custom_config = {
            "tasks": {"task.completed": 50},
        }
        handler = GamificationEventHandler(
            db=db_session,
            tenant_id=test_tenant.id,
            config=custom_config,
        )

        points = handler._calculate_points(
            event_type="task.completed",
            source_module="tasks",
            metadata={"priority": "medium"},
        )
        assert points == 50
