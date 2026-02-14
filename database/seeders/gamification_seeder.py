"""Gamification badges seeder for development environment.

Creates default badges for all tenants.
This seeder is idempotent - it will not create duplicate badges.
"""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.gamification import Badge
from app.models.tenant import Tenant

INITIAL_BADGES = [
    {
        "name": "Early Bird",
        "description": "Completa 10 tareas antes del deadline",
        "icon": "sunrise",
        "criteria": {
            "event_type": "task.completed",
            "count": 10,
        },
        "points_value": 50,
    },
    {
        "name": "Streak Master",
        "description": "Mantén una racha de actividad de 7 días consecutivos",
        "icon": "flame",
        "criteria": {
            "event_type": "task.completed",
            "count": 7,
        },
        "points_value": 100,
    },
    {
        "name": "Speed Demon",
        "description": "Completa 5 tareas en un solo día",
        "icon": "zap",
        "criteria": {
            "event_type": "task.completed",
            "count": 5,
        },
        "points_value": 75,
    },
    {
        "name": "Task Master",
        "description": "Completa 50 tareas en total",
        "icon": "trophy",
        "criteria": {
            "event_type": "task.completed",
            "count": 50,
        },
        "points_value": 200,
    },
    {
        "name": "First Steps",
        "description": "Completa tu primera tarea",
        "icon": "footprints",
        "criteria": {
            "event_type": "task.completed",
            "count": 1,
        },
        "points_value": 10,
    },
    {
        "name": "Team Player",
        "description": "Asiste a 10 eventos de calendario",
        "icon": "users",
        "criteria": {
            "event_type": "calendar.event_attended",
            "count": 10,
        },
        "points_value": 75,
    },
    {
        "name": "Organizer",
        "description": "Crea 25 tareas para tu equipo",
        "icon": "clipboard-list",
        "criteria": {
            "event_type": "task.created",
            "count": 25,
        },
        "points_value": 50,
    },
    {
        "name": "Century Club",
        "description": "Alcanza 100 tareas completadas",
        "icon": "award",
        "criteria": {
            "event_type": "task.completed",
            "count": 100,
        },
        "points_value": 500,
    },
]


class GamificationSeeder(Seeder):
    """Seeder for initial gamification badges.

    Creates:
    - 8 predefined badges per tenant

    This seeder is idempotent - it will not create duplicate badges.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        tenants = db.query(Tenant).all()

        for tenant in tenants:
            for badge_data in INITIAL_BADGES:
                existing = (
                    db.query(Badge)
                    .filter(
                        Badge.tenant_id == tenant.id,
                        Badge.name == badge_data["name"],
                    )
                    .first()
                )

                if not existing:
                    badge = Badge(
                        tenant_id=tenant.id,
                        name=badge_data["name"],
                        description=badge_data["description"],
                        icon=badge_data["icon"],
                        criteria=badge_data["criteria"],
                        points_value=badge_data["points_value"],
                    )
                    db.add(badge)

        db.commit()
