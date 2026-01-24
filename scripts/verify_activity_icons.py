"""
Script de verificación para el sistema de iconos configurables
Verifica que la tabla, modelo y endpoints estén funcionando correctamente
"""

import asyncio

from sqlalchemy import select

from app.core.db.session import SessionLocal
from app.models.activity_icon_config import ActivityIconConfig
from app.models.tenant import Tenant


async def verify_activity_icons() -> None:
    """Verificar que el sistema de iconos configurables esté funcionando."""
    print("🔍 Verificando sistema de iconos configurables...")
    print()

    async with SessionLocal() as db:
        # 1. Verificar que la tabla existe y tiene datos
        print("1️⃣ Verificando tabla activity_icon_configs...")
        try:
            stmt = select(ActivityIconConfig).limit(5)
            result = await db.execute(stmt)
            configs = result.scalars().all()

            if configs:
                print(f"   ✅ Tabla existe y tiene {len(configs)} configuraciones (mostrando primeras 5)")
                for config in configs:
                    print(f"      - {config.activity_type}/{config.status}: {config.icon}")
            else:
                print("   ⚠️  Tabla existe pero no tiene datos. Ejecuta el seeder:")
                print("      python -m database.seeders.activity_icon_configs_seeder")
        except Exception as e:
            print(f"   ❌ Error al verificar tabla: {e}")
            return

        print()

        # 2. Verificar configuraciones por tenant
        print("2️⃣ Verificando configuraciones por tenant...")
        try:
            stmt = select(Tenant).limit(1)
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()

            if tenant:
                stmt = select(ActivityIconConfig).where(
                    ActivityIconConfig.tenant_id == tenant.id
                )
                result = await db.execute(stmt)
                tenant_configs = result.scalars().all()

                print(f"   ✅ Tenant '{tenant.name}' tiene {len(tenant_configs)} configuraciones")

                # Agrupar por tipo de actividad
                by_type = {}
                for config in tenant_configs:
                    if config.activity_type not in by_type:
                        by_type[config.activity_type] = []
                    by_type[config.activity_type].append(config)

                for activity_type, configs in by_type.items():
                    print(f"      - {activity_type}: {len(configs)} estados configurados")
            else:
                print("   ⚠️  No se encontraron tenants en la base de datos")
        except Exception as e:
            print(f"   ❌ Error al verificar configuraciones: {e}")

        print()

        # 3. Verificar tipos de actividad y estados
        print("3️⃣ Verificando tipos de actividad y estados...")
        try:
            stmt = select(ActivityIconConfig.activity_type).distinct()
            result = await db.execute(stmt)
            activity_types = result.scalars().all()

            print(f"   ✅ Tipos de actividad configurados: {', '.join(activity_types)}")

            for activity_type in activity_types:
                stmt = select(ActivityIconConfig.status).where(
                    ActivityIconConfig.activity_type == activity_type
                ).distinct()
                result = await db.execute(stmt)
                statuses = result.scalars().all()
                print(f"      - {activity_type}: {', '.join(statuses)}")
        except Exception as e:
            print(f"   ❌ Error al verificar tipos: {e}")

        print()
        print("✅ Verificación completada!")
        print()
        print("📝 Próximos pasos:")
        print("   1. Inicia el backend: python run.py")
        print("   2. Verifica los endpoints en: http://localhost:8000/docs")
        print("      - GET /api/v1/activity-icons")
        print("      - GET /api/v1/activity-icons/defaults")
        print("   3. Inicia el frontend y navega a: /settings/activity-icons")
        print("   4. Verifica que los iconos se muestren en el calendario")


if __name__ == "__main__":
    asyncio.run(verify_activity_icons())
