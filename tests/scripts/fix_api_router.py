#!/usr/bin/env python3
"""
Script para reparar el problema del api_router usando lazy loading.
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def create_lazy_api_router():
    """Crea una versión del api_router con lazy loading."""
    print("🔧 CREANDO API ROUTER CON LAZY LOADING")
    print("=" * 50)

    lazy_router_content = '''"""
API Router con lazy loading para evitar timeouts en imports.
"""

from typing import TYPE_CHECKING
from fastapi import APIRouter

if TYPE_CHECKING:
    # Solo para type checking - no se ejecuta en runtime
    pass

# Cache para el router
_api_router = None

def get_api_router() -> APIRouter:
    """Obtiene el API router con lazy loading."""
    global _api_router
    
    if _api_router is not None:
        return _api_router
    
    print("🔄 Creando API router (lazy loading)...")
    
    # Importar todos los módulos necesarios
    from app.api.v1 import (
        activities,
        activity_icons,
        approvals,
        auth,
        automation,
        comments,
        config,
        contact_methods,
        files,
        flow_runs,
        folders,
        import_export,
        integrations,
        notifications,
        preferences,
        pubsub,
        reporting,
        search,
        sse,
        tags,
        templates,
        users,
        views,
        workflows,
    )
    from app.modules.calendar.api import router as calendar_router
    from app.modules.crm.api import router as crm_router
    from app.modules.inventory.api import router as inventory_router
    from app.modules.products.api import router as products_router
    from app.modules.tasks.api import router as tasks_router
    from app.features.tasks.statuses import router as task_statuses_router
    
    # Crear el router
    _api_router = APIRouter()
    
    # Incluir todos los routers
    _api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    _api_router.include_router(users.router, prefix="/users", tags=["users"])
    _api_router.include_router(products_router, prefix="/products", tags=["products"])
    _api_router.include_router(config.router, prefix="/config", tags=["config"])
    _api_router.include_router(pubsub.router, prefix="/pubsub", tags=["pubsub"])
    _api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
    _api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
    _api_router.include_router(reporting.router, prefix="/reporting", tags=["reporting"])
    _api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
    _api_router.include_router(files.router, prefix="/files", tags=["files"])
    _api_router.include_router(flow_runs.router, prefix="/flow-runs", tags=["flow-runs"])
    _api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
    _api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
    _api_router.include_router(activity_icons.router, tags=["activity-icons"])
    _api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
    _api_router.include_router(task_statuses_router, prefix="/task-statuses", tags=["task-statuses"])
    _api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
    _api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
    _api_router.include_router(search.router, prefix="/search", tags=["search"])
    _api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
    _api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
    _api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
    _api_router.include_router(crm_router, prefix="/crm", tags=["crm"])
    _api_router.include_router(import_export.router, prefix="/import-export", tags=["import-export"])
    _api_router.include_router(views.router, prefix="/views", tags=["views"])
    _api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
    _api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
    _api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
    _api_router.include_router(contact_methods.router, prefix="/contact-methods", tags=["contact-methods"])
    _api_router.include_router(sse.router, tags=["sse"])
    
    print("✅ API router creado exitosamente")
    return _api_router

# Para compatibilidad con el código existente
api_router = get_api_router()
'''

    lazy_router_path = backend_path / "app" / "api" / "v1" / "lazy_router.py"

    try:
        with open(lazy_router_path, 'w', encoding='utf-8') as f:
            f.write(lazy_router_content)

        print(f"✅ Lazy router creado en: {lazy_router_path}")
        return True

    except Exception as e:
        print(f"❌ Error creando lazy router: {e}")
        return False

def modify_main_to_use_lazy_router():
    """Modifica main.py para usar el lazy router."""
    print("\n🔧 MODIFICANDO main.py PARA USAR LAZY ROUTER")
    print("=" * 50)

    main_path = backend_path / "app" / "main.py"

    try:
        with open(main_path, encoding='utf-8') as f:
            content = f.read()

        # Reemplazar el import del api_router
        old_import = "from app.api.v1 import api_router"
        new_import = "from app.api.v1.lazy_router import get_api_router"

        if old_import in content:
            content = content.replace(old_import, new_import)
            print("   📝 Import de api_router reemplazado")
        else:
            print("   ⚠️ No se encontró el import original")

        # Reemplazar el uso del api_router
        old_usage = "app.include_router(api_router, prefix=\"/api/v1\")"
        new_usage = "app.include_router(get_api_router(), prefix=\"/api/v1\")"

        if old_usage in content:
            content = content.replace(old_usage, new_usage)
            print("   📝 Uso de api_router reemplazado")
        else:
            print("   ⚠️ No se encontró el uso original")

        # Guardar el archivo modificado
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print("✅ main.py modificado exitosamente")
        return True

    except Exception as e:
        print(f"❌ Error modificando main.py: {e}")
        return False

def create_backup_original():
    """Crea una copia de seguridad del archivo original."""
    print("\n💾 CREANDO COPIA DE SEGURIDAD")
    print("=" * 50)

    original_path = backend_path / "app" / "api" / "v1" / "__init__.py"
    backup_path = backend_path / "app" / "api" / "v1" / "__init__.py.backup"

    try:
        with open(original_path, encoding='utf-8') as f:
            content = f.read()

        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Copia de seguridad creada en: {backup_path}")
        return True

    except Exception as e:
        print(f"❌ Error creando copia de seguridad: {e}")
        return False

def test_lazy_import():
    """Prueba el import del lazy router."""
    print("\n🧪 PROBANDO LAZY ROUTER")
    print("=" * 50)

    try:
        # Importar el lazy router
        from app.api.v1.lazy_router import get_api_router

        print("   📦 Import exitoso")

        # Intentar obtener el router (esto debería tomar más tiempo)
        import threading
        import time

        result = [None]
        exception = [None]

        def get_router_thread():
            try:
                start_time = time.time()
                router = get_api_router()
                elapsed = time.time() - start_time
                result[0] = (True, elapsed, router)
            except Exception as e:
                exception[0] = str(e)
                result[0] = (False, 0, None)

        thread = threading.Thread(target=get_router_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=10)  # Darle 10 segundos

        if thread.is_alive():
            print("   ⏰ TIMEOUT creando el router")
            return False
        elif result[0] and result[0][0]:
            success, elapsed, router = result[0]
            print(f"   ✅ Router creado en {elapsed:.2f}s")
            return True
        else:
            print(f"   ❌ Error: {exception[0]}")
            return False

    except Exception as e:
        print(f"   ❌ Error importando lazy router: {e}")
        return False

def main():
    """Función principal."""
    print("🔧 REPARACIÓN DEFINITIVA DEL API ROUTER")
    print("=" * 60)

    success_count = 0
    total_tasks = 4

    # Tarea 1: Crear copia de seguridad
    if create_backup_original():
        success_count += 1

    # Tarea 2: Crear lazy router
    if create_lazy_api_router():
        success_count += 1

    # Tarea 3: Modificar main.py
    if modify_main_to_use_lazy_router():
        success_count += 1

    # Tarea 4: Probar lazy import
    if test_lazy_import():
        success_count += 1

    print("\n📊 RESUMEN")
    print("=" * 50)
    print(f"Tareas completadas: {success_count}/{total_tasks}")

    if success_count == total_tasks:
        print("✅ Reparación completada exitosamente")
        print("\n💡 PASOS SIGUIENTES:")
        print("1. Reinicia el servidor: uvicorn app.main:app --reload")
        print("2. El servidor debería iniciar sin timeouts")
        print("3. El API router se creará cuando se necesite")
        print("4. Si hay problemas, restaura el backup:")
        print("   cp app/api/v1/__init__.py.backup app/api/v1/__init__.py")
    else:
        print("❌ Algunas tareas fallaron")
        print("💡 Revisa los errores e intenta manualmente")

    return success_count == total_tasks

if __name__ == "__main__":
    main()
