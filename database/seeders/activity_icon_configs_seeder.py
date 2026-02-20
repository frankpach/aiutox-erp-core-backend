"""Activity Icon Configs Seeder
Populates default icon configurations for activity types and statuses
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.activity_icon_config import ActivityIconConfig
from app.models.tenant import Tenant

# Configuraciones de iconos por defecto
DEFAULT_ICON_CONFIGS = {
    "task": {
        "todo": {"icon": "📋", "class_name": "text-white/90"},
        "pending": {"icon": "📋", "class_name": "text-white/90"},
        "in_progress": {"icon": "⚡", "class_name": "text-white"},
        "done": {"icon": "✅", "class_name": "text-white"},
        "completed": {"icon": "✅", "class_name": "text-white"},
        "canceled": {"icon": "🚫", "class_name": "text-white"},
        "blocked": {"icon": "🛑", "class_name": "text-white"},
    },
    "meeting": {
        "todo": {"icon": "👥", "class_name": "text-white/90"},
        "pending": {"icon": "👥", "class_name": "text-white/90"},
        "in_progress": {"icon": "🎯", "class_name": "text-white"},
        "done": {"icon": "✅", "class_name": "text-white"},
        "completed": {"icon": "✅", "class_name": "text-white"},
        "canceled": {"icon": "🚫", "class_name": "text-white"},
        "blocked": {"icon": "🛑", "class_name": "text-white"},
    },
    "event": {
        "todo": {"icon": "📅", "class_name": "text-white/90"},
        "pending": {"icon": "📅", "class_name": "text-white/90"},
        "in_progress": {"icon": "🎪", "class_name": "text-white"},
        "done": {"icon": "✅", "class_name": "text-white"},
        "completed": {"icon": "✅", "class_name": "text-white"},
        "canceled": {"icon": "🚫", "class_name": "text-white"},
        "blocked": {"icon": "🛑", "class_name": "text-white"},
    },
    "project": {
        "todo": {"icon": "🚀", "class_name": "text-white/90"},
        "pending": {"icon": "🚀", "class_name": "text-white/90"},
        "in_progress": {"icon": "🔧", "class_name": "text-white"},
        "done": {"icon": "✅", "class_name": "text-white"},
        "completed": {"icon": "✅", "class_name": "text-white"},
        "canceled": {"icon": "🚫", "class_name": "text-white"},
        "blocked": {"icon": "🛑", "class_name": "text-white"},
    },
    "workflow": {
        "todo": {"icon": "⚙️", "class_name": "text-white/90"},
        "pending": {"icon": "⚙️", "class_name": "text-white/90"},
        "in_progress": {"icon": "🔄", "class_name": "text-white"},
        "done": {"icon": "✅", "class_name": "text-white"},
        "completed": {"icon": "✅", "class_name": "text-white"},
        "canceled": {"icon": "🚫", "class_name": "text-white"},
        "blocked": {"icon": "🛑", "class_name": "text-white"},
    },
}


class ActivityIconConfigsSeeder(Seeder):
    """Seeder for activity icon configurations."""

    def run(self, db: Session) -> None:
        """
        Seed default activity icon configurations for all tenants.

        Args:
            db: Database session
        """
        print("🎨 Seeding activity icon configurations...")

        # Obtener todos los tenants
        tenants = db.query(Tenant).all()

        if not tenants:
            print("⚠️  No tenants found. Skipping activity icon configs seeding.")
            return

        configs_created = 0
        configs_skipped = 0

        for tenant in tenants:
            print(f"  Processing tenant: {tenant.name} ({tenant.id})")

            for activity_type, statuses in DEFAULT_ICON_CONFIGS.items():
                for status, config in statuses.items():
                    # Verificar si ya existe la configuración
                    existing = db.query(ActivityIconConfig).filter(
                        ActivityIconConfig.tenant_id == tenant.id,
                        ActivityIconConfig.activity_type == activity_type,
                        ActivityIconConfig.status == status,
                    ).first()

                    if existing:
                        configs_skipped += 1
                        continue

                    # Crear nueva configuración
                    new_config = ActivityIconConfig(
                        id=uuid.uuid4(),
                        tenant_id=tenant.id,
                        activity_type=activity_type,
                        status=status,
                        icon=config["icon"],
                        class_name=config["class_name"],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )

                    db.add(new_config)
                    configs_created += 1

        db.commit()

        print("✅ Activity icon configs seeding completed!")
        print(f"   - Created: {configs_created}")
        print(f"   - Skipped (already exist): {configs_skipped}")
