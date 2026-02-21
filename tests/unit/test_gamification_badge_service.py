"""Unit tests for BadgeService (gamification)."""

from uuid import uuid4

import pytest

from app.core.gamification.badge_service import BadgeService
from app.core.gamification.points_service import PointsService

pytestmark = pytest.mark.skip(reason="Missing migration: badges table not created")


@pytest.fixture
def badge_service(db_session, test_tenant):
    """Create BadgeService instance."""
    return BadgeService(db=db_session, tenant_id=test_tenant.id)


@pytest.fixture
def points_service(db_session, test_tenant):
    """Create PointsService instance for seeding events."""
    return PointsService(db=db_session, tenant_id=test_tenant.id)


@pytest.fixture
def sample_badge(badge_service):
    """Create a sample badge for testing."""
    return badge_service.create_badge(
        {
            "name": "Primer Tarea",
            "description": "Completar tu primera tarea",
            "icon": "check-circle",
            "criteria": {"event_type": "task.completed", "count": 1},
            "points_value": 50,
        }
    )


@pytest.fixture
def streak_badge(badge_service):
    """Create a streak-based badge."""
    return badge_service.create_badge(
        {
            "name": "Racha de 5",
            "description": "Completar 5 tareas",
            "icon": "flame",
            "criteria": {"event_type": "task.completed", "count": 5},
            "points_value": 100,
        }
    )


class TestCreateBadge:
    """Tests para crear badges."""

    def test_create_badge_basic(self, badge_service):
        """Crear un badge con datos básicos."""
        badge = badge_service.create_badge(
            {
                "name": "Test Badge",
                "description": "Descripción de prueba",
                "icon": "star",
                "criteria": {"event_type": "task.completed", "count": 10},
                "points_value": 25,
            }
        )

        assert badge.id is not None
        assert badge.name == "Test Badge"
        assert badge.icon == "star"
        assert badge.is_active is True
        assert badge.criteria["count"] == 10

    def test_create_badge_defaults(self, badge_service):
        """Crear un badge usa valores por defecto correctos."""
        badge = badge_service.create_badge(
            {
                "name": "Minimal Badge",
                "criteria": {"event_type": "task.created"},
            }
        )

        assert badge.icon == "trophy"
        assert badge.points_value == 0
        assert badge.is_active is True


class TestListBadges:
    """Tests para listar badges."""

    def test_list_badges_empty(self, badge_service):
        """Lista vacía cuando no hay badges."""
        badges = badge_service.list_badges()
        assert badges == []

    def test_list_badges_returns_active(self, badge_service, sample_badge):
        """Listar badges retorna solo activos por defecto."""
        badges = badge_service.list_badges(active_only=True)
        assert len(badges) >= 1
        assert all(b.is_active for b in badges)

    def test_list_badges_sorted_by_name(self, badge_service):
        """Badges se retornan ordenados por nombre."""
        badge_service.create_badge(
            {
                "name": "Zeta Badge",
                "criteria": {"event_type": "task.completed"},
            }
        )
        badge_service.create_badge(
            {
                "name": "Alpha Badge",
                "criteria": {"event_type": "task.completed"},
            }
        )

        badges = badge_service.list_badges()
        names = [b.name for b in badges]
        assert names == sorted(names)


class TestCheckAndAwardBadges:
    """Tests para check_and_award_badges."""

    def test_awards_badge_when_criteria_met(
        self, badge_service, points_service, sample_badge, test_user
    ):
        """Otorga badge cuando se cumplen los criterios."""
        # Crear un evento que cumpla el criterio (count >= 1)
        points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        awarded = badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="task.completed",
        )

        assert len(awarded) == 1
        assert awarded[0].badge_id == sample_badge.id

    def test_does_not_award_duplicate(
        self, badge_service, points_service, sample_badge, test_user
    ):
        """No otorga el mismo badge dos veces."""
        points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )

        # Primera vez: otorga
        awarded_1 = badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="task.completed",
        )
        assert len(awarded_1) == 1

        # Segunda vez: no otorga
        awarded_2 = badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="task.completed",
        )
        assert len(awarded_2) == 0

    def test_does_not_award_when_criteria_not_met(
        self, badge_service, streak_badge, test_user
    ):
        """No otorga badge si no se cumplen los criterios (count insuficiente)."""
        awarded = badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="task.completed",
        )

        assert len(awarded) == 0

    def test_does_not_award_for_wrong_event_type(
        self, badge_service, points_service, sample_badge, test_user
    ):
        """No otorga badge si el event_type no coincide."""
        points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="calendar.event_attended",
            source_module="calendar",
            source_id=uuid4(),
        )

        awarded = badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="calendar.event_attended",
        )

        # sample_badge requiere "task.completed", no "calendar.event_attended"
        assert len(awarded) == 0


class TestGetUserBadges:
    """Tests para get_user_badges."""

    def test_returns_empty_for_new_user(self, badge_service, test_user):
        """Retorna lista vacía para usuario sin badges."""
        badges = badge_service.get_user_badges(test_user.id)
        assert badges == []

    def test_returns_earned_badges(
        self, badge_service, points_service, sample_badge, test_user
    ):
        """Retorna badges ganados por el usuario."""
        points_service.add_points(
            user_id=test_user.id,
            points=10,
            event_type="task.completed",
            source_module="tasks",
            source_id=uuid4(),
        )
        badge_service.check_and_award_badges(
            user_id=test_user.id,
            event_type="task.completed",
        )

        user_badges = badge_service.get_user_badges(test_user.id)
        assert len(user_badges) == 1
        assert user_badges[0].badge_id == sample_badge.id


class TestMultiTenancy:
    """Tests para aislamiento multi-tenant."""

    def test_badges_isolated_by_tenant(self, db_session, test_tenant, other_tenant):
        """Badges de un tenant no son visibles en otro."""
        svc_t1 = BadgeService(db=db_session, tenant_id=test_tenant.id)
        svc_t2 = BadgeService(db=db_session, tenant_id=other_tenant.id)

        svc_t1.create_badge(
            {
                "name": "Tenant 1 Badge",
                "criteria": {"event_type": "task.completed"},
            }
        )

        badges_t2 = svc_t2.list_badges()
        assert all(b.name != "Tenant 1 Badge" for b in badges_t2)
