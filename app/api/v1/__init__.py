"""API v1 router aggregation."""

from fastapi import APIRouter

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

api_router = APIRouter()

# Include module routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(pubsub.router, prefix="/pubsub", tags=["pubsub"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(
    preferences.router, prefix="/preferences", tags=["preferences"]
)
api_router.include_router(reporting.router, prefix="/reporting", tags=["reporting"])
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(flow_runs.router, prefix="/flow-runs", tags=["flow-runs"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(activity_icons.router, tags=["activity-icons"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(
    task_statuses_router, prefix="/task-statuses", tags=["task-statuses"]
)
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(
    integrations.router, prefix="/integrations", tags=["integrations"]
)
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
api_router.include_router(crm_router, prefix="/crm", tags=["crm"])
api_router.include_router(
    import_export.router, prefix="/import-export", tags=["import-export"]
)
api_router.include_router(views.router, prefix="/views", tags=["views"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(
    contact_methods.router, prefix="/contact-methods", tags=["contact-methods"]
)
api_router.include_router(sse.router, tags=["sse"])
