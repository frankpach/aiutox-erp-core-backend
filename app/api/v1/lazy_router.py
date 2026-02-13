"""
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
        calendar,
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
    from app.features.tasks.statuses import router as task_statuses_router
    from app.modules.crm.api import router as crm_router
    from app.modules.inventory.api import router as inventory_router
    from app.modules.products.api import router as products_router
    from app.modules.tasks.api import router as tasks_router

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
    _api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
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
