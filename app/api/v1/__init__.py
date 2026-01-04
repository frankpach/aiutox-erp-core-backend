"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    activities,
    approvals,
    auth,
    automation,
    comments,
    config,
    files,
    folders,
    import_export,
    integrations,
    notifications,
    preferences,
    pubsub,
    reporting,
    search,
    tags,
    templates,
    users,
    views,
    workflows,
)
from app.modules.products.api import router as products_router
from app.modules.tasks.api import router as tasks_router
from app.modules.calendar.api import router as calendar_router
from app.modules.inventory.api import router as inventory_router
from app.modules.crm.api import router as crm_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(pubsub.router, prefix="/pubsub", tags=["pubsub"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["preferences"])
api_router.include_router(reporting.router, prefix="/reporting", tags=["reporting"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(crm_router, prefix="/crm", tags=["crm"])
api_router.include_router(import_export.router, prefix="/import-export", tags=["import-export"])
api_router.include_router(views.router, prefix="/views", tags=["views"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
