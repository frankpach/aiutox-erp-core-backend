"""Unit tests for PointsService (gamification)."""

from datetime import date
from uuid import uuid4

import pytest

from app.core.gamification.points_service import PointsService

_SKIP_DB = pytest.mark.skip(reason="Missing migration: user_points table not created")


@pytest.fixture
def points_service(db_session, test_tenant):
    """Create PointsService instance."""
    return PointsService(db=db_session, tenant_id=test_tenant.id)


class TestCalculateLevel:
    """Tests for the static calculate_level method (no DB needed)."""

    def test_level_1_for_zero_points(self):
        assert PointsService.calculate_level(0) == 1

    def test_level_1_for_negative_points(self):
        assert PointsService.calculate_level(-10) == 1

    def test_level_1_for_99_points(self):
        assert PointsService.calculate_level(99) == 1

    def test_level_2_at_100_points(self):
        assert PointsService.calculate_level(100) == 2

    def test_level_2_at_399_points(self):
        assert PointsService.calculate_level(399) == 2

    def test_level_3_at_400_points(self):
        assert PointsService.calculate_level(400) == 3

    def test_level_4_at_900_points(self):
        assert PointsService.calculate_level(900) == 4

    def test_high_points(self):
        """Nivel alto con muchos puntos."""
        level = PointsService.calculate_level(10000)
        assert level == 11


class TestPointsForLevel:
    """Tests for the static points_for_level method."""

    def test_level_1_needs_0_points(self):
        assert PointsService.points_for_level(1) == 0

    def test_level_0_needs_0_points(self):
        assert PointsService.points_for_level(0) == 0

    def test_level_2_needs_100_points(self):
        assert PointsService.points_for_level(2) == 100

    def test_level_3_needs_400_points(self):
        assert PointsService.points_for_level(3) == 400

    def test_level_4_needs_900_points(self):
        assert PointsService.points_for_level(4) == 900


@_SKIP_DB
class TestAddPoints:
    """Tests for add_points (requires DB)."""

    def test_add_points_creates_user_points(self, points_service, test_user):
        """Agregar puntos crea registro UserPoints si no existe."""
        result = points_service.add_points(
            user_id=test_user.id,
            points=50,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        assert result.total_points == 50
        assert result.level == 1
        assert result.user_id == test_user.id

    def test_add_points_accumulates(self, points_service, test_user):
        """Puntos se acumulan correctamente."""
        task_id_1 = uuid4()
        task_id_2 = uuid4()

        points_service.add_points(
            user_id=test_user.id,
            points=50,
            event_type="task.completed",
            source_module="tasks",
            source_id=task_id_1,
        )
        result = points_service.add_points(
            user_id=test_user.id,
            points=60,
            event_type="task.completed",
            source_module="tasks",
            source_id=task_id_2,
        )

        assert result.total_points == 110

    def test_add_points_triggers_level_up(self, points_service, test_user):
        """Agregar puntos suficientes sube de nivel."""
        result = points_service.add_points(
            user_id=test_user.id,
            points=100,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        assert result.level == 2

    def test_add_points_records_event(self, points_service, test_user):
        """Cada add_points registra un GamificationEvent."""
        source_id = uuid4()
        points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="task.created",
            source_module="tasks",
            source_id=source_id,
            metadata={"priority": "high"},
        )

        events = points_service.get_user_events(test_user.id)
        assert len(events) == 1
        assert events[0].event_type == "task.created"
        assert events[0].points_earned == 10
        assert events[0].source_id == source_id

    def test_add_points_updates_streak(self, points_service, test_user):
        """Agregar puntos actualiza la racha diaria."""
        result = points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        assert result.current_streak == 1
        assert result.last_activity_date == date.today()


@_SKIP_DB
class TestGetUserPoints:
    """Tests for get_user_points."""

    def test_returns_none_for_unknown_user(self, points_service):
        """Retorna None si el usuario no tiene registro."""
        result = points_service.get_user_points(uuid4())
        assert result is None

    def test_returns_user_points(self, points_service, test_user):
        """Retorna el registro de puntos del usuario."""
        points_service.add_points(
            user_id=test_user.id,
            points=25,
            event_type="task.created",
            source_module="tasks",
            source_id=uuid4(),
        )

        result = points_service.get_user_points(test_user.id)
        assert result is not None
        assert result.total_points == 25


@_SKIP_DB
class TestMultiTenancy:
    """Tests para aislamiento multi-tenant."""

    def test_points_isolated_by_tenant(
        self, db_session, test_tenant, test_user, other_tenant, other_user
    ):
        """Puntos de un tenant no son visibles en otro."""
        svc_t1 = PointsService(db=db_session, tenant_id=test_tenant.id)
        svc_t2 = PointsService(db=db_session, tenant_id=other_tenant.id)

        svc_t1.add_points(
            user_id=test_user.id,
            points=100,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        # El otro tenant no ve los puntos
        result = svc_t2.get_user_points(test_user.id)
        assert result is None
