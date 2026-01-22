"""Task statuses seeder for development environment.

Creates default task statuses for all tenants and additional custom statuses
for development testing.

This seeder is idempotent - it will not create duplicate statuses.
"""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.task_status import TaskStatus
from app.models.tenant import Tenant


class TaskStatusesSeeder(Seeder):
    """Seeder for task statuses with base system statuses and custom examples.

    Creates:
    - Base system statuses (5): Por Iniciar, En Proceso, Pausado, Cancelado, Completado
    - Custom statuses (3): En Revisión, Bloqueado, Aprobado

    This seeder is idempotent - it will not create duplicate statuses.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get all tenants
        tenants = db.query(Tenant).all()

        # Base system statuses (cannot be deleted)
        base_statuses = [
            {"name": "Por Iniciar", "type": "open", "color": "#2196F3", "is_system": True, "order": 1},
            {"name": "En Proceso", "type": "in_progress", "color": "#FF9800", "is_system": True, "order": 2},
            {"name": "Pausado", "type": "in_progress", "color": "#FFC107", "is_system": True, "order": 3},
            {"name": "Cancelado", "type": "closed", "color": "#F44336", "is_system": True, "order": 4},
            {"name": "Completado", "type": "closed", "color": "#4CAF50", "is_system": True, "order": 5},
        ]

        # Custom statuses for development (can be deleted)
        custom_statuses = [
            {"name": "En Revisión", "type": "in_progress", "color": "#9C27B0", "is_system": False, "order": 6},
            {"name": "Bloqueado", "type": "in_progress", "color": "#607D8B", "is_system": False, "order": 7},
            {"name": "Aprobado", "type": "closed", "color": "#00BCD4", "is_system": False, "order": 8},
        ]

        for tenant in tenants:
            # Create base system statuses
            for status_data in base_statuses:
                existing = (
                    db.query(TaskStatus)
                    .filter(
                        TaskStatus.tenant_id == tenant.id,
                        TaskStatus.name == status_data["name"],
                        TaskStatus.is_system.is_(True),
                    )
                    .first()
                )

                if not existing:
                    status = TaskStatus(
                        tenant_id=tenant.id,
                        name=status_data["name"],
                        type=status_data["type"],
                        color=status_data["color"],
                        is_system=status_data["is_system"],
                        order=status_data["order"],
                    )
                    db.add(status)

            # Create custom statuses for development
            for status_data in custom_statuses:
                existing = (
                    db.query(TaskStatus)
                    .filter(
                        TaskStatus.tenant_id == tenant.id,
                        TaskStatus.name == status_data["name"],
                    )
                    .first()
                )

                if not existing:
                    status = TaskStatus(
                        tenant_id=tenant.id,
                        name=status_data["name"],
                        type=status_data["type"],
                        color=status_data["color"],
                        is_system=status_data["is_system"],
                        order=status_data["order"],
                    )
                    db.add(status)

        db.commit()
