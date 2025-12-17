"""Preferences router for user personalization."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.preferences.dashboards import DashboardsService
from app.core.preferences.service import PreferencesService
from app.core.preferences.views import ViewsService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.preference import (
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    NotificationPreferencesRequest,
    NotificationPreferenceSchema,
    PreferenceSetRequest,
    SavedViewCreate,
    SavedViewResponse,
    SavedViewUpdate,
)

router = APIRouter()


def get_preferences_service(
    db: Annotated[Session, Depends(get_db)],
) -> PreferencesService:
    """Dependency to get PreferencesService."""
    return PreferencesService(db)


def get_views_service(db: Annotated[Session, Depends(get_db)]) -> ViewsService:
    """Dependency to get ViewsService."""
    return ViewsService(db)


def get_dashboards_service(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardsService:
    """Dependency to get DashboardsService."""
    return DashboardsService(db)


@router.get(
    "",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get user preferences",
    description="Get all preferences for the current user with inheritance. Requires preferences.view permission.",
)
async def get_preferences(
    current_user: Annotated[User, Depends(require_permission("preferences.view"))],
    service: Annotated[PreferencesService, Depends(get_preferences_service)],
    preference_type: str | None = Query(None, description="Filter by preference type"),
) -> StandardResponse[dict[str, Any]]:
    """Get all preferences for the current user."""
    preferences = service.get_all_preferences(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        preference_type=preference_type,
    )
    return StandardResponse(
        data=preferences,
        message="Preferences retrieved successfully",
    )


@router.put(
    "",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Update user preferences",
    description="Update preferences for the current user. Requires preferences.manage permission.",
)
async def update_preferences(
    preference_data: PreferenceSetRequest,
    current_user: Annotated[User, Depends(require_permission("preferences.manage"))],
    service: Annotated[PreferencesService, Depends(get_preferences_service)],
    preference_type: str = Query(..., description="Preference type (e.g., 'basic', 'notification')"),
) -> StandardResponse[dict[str, Any]]:
    """Update preferences for the current user."""
    updated = {}
    for key, value in preference_data.preferences.items():
        result = service.set_preference(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            preference_type=preference_type,
            key=key,
            value=value,
        )
        updated[key] = result["value"]

    return StandardResponse(
        data=updated,
        message="Preferences updated successfully",
    )


@router.get(
    "/org",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get organization preferences",
    description="Get organization preferences. Requires preferences.view permission.",
)
async def get_org_preferences(
    current_user: Annotated[User, Depends(require_permission("preferences.view"))],
    db: Annotated[Session, Depends(get_db)],
    preference_type: str | None = Query(None, description="Filter by preference type"),
) -> StandardResponse[dict[str, Any]]:
    """Get organization preferences."""
    from app.repositories.preference_repository import PreferenceRepository

    repository = PreferenceRepository(db)
    org_prefs = repository.get_all_org_preferences(
        current_user.tenant_id, preference_type
    )
    preferences = {pref.key: pref.value for pref in org_prefs}

    return StandardResponse(
        data=preferences,
        message="Organization preferences retrieved successfully",
    )


@router.put(
    "/org",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Update organization preferences",
    description="Update organization preferences. Requires preferences.manage permission.",
)
async def update_org_preferences(
    preference_data: PreferenceSetRequest,
    current_user: Annotated[User, Depends(require_permission("preferences.manage"))],
    service: Annotated[PreferencesService, Depends(get_preferences_service)],
    preference_type: str = Query(..., description="Preference type"),
) -> StandardResponse[dict[str, Any]]:
    """Update organization preferences."""
    updated = {}
    for key, value in preference_data.preferences.items():
        result = service.set_org_preference(
            tenant_id=current_user.tenant_id,
            preference_type=preference_type,
            key=key,
            value=value,
        )
        updated[key] = result["value"]

    return StandardResponse(
        data=updated,
        message="Organization preferences updated successfully",
    )


@router.get(
    "/notifications",
    response_model=StandardResponse[dict[str, NotificationPreferenceSchema]],
    status_code=status.HTTP_200_OK,
    summary="Get notification preferences",
    description="Get notification preferences for the current user. Requires preferences.view permission.",
)
async def get_notification_preferences(
    current_user: Annotated[User, Depends(require_permission("preferences.view"))],
    service: Annotated[PreferencesService, Depends(get_preferences_service)],
) -> StandardResponse[dict[str, NotificationPreferenceSchema]]:
    """Get notification preferences."""
    all_prefs = service.get_all_preferences(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        preference_type="notification",
    )

    # Convert to NotificationPreferenceSchema format
    notification_prefs = {}
    for key, value in all_prefs.items():
        if isinstance(value, dict):
            notification_prefs[key] = NotificationPreferenceSchema(**value)
        else:
            notification_prefs[key] = NotificationPreferenceSchema()

    return StandardResponse(
        data=notification_prefs,
        message="Notification preferences retrieved successfully",
    )


@router.put(
    "/notifications",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Update notification preferences",
    description="Update notification preferences for the current user. Requires preferences.manage permission.",
)
async def update_notification_preferences(
    notification_data: NotificationPreferencesRequest,
    current_user: Annotated[User, Depends(require_permission("preferences.manage"))],
    service: Annotated[PreferencesService, Depends(get_preferences_service)],
) -> StandardResponse[dict[str, Any]]:
    """Update notification preferences."""
    updated = {}
    for event_type, pref_schema in notification_data.preferences.items():
        result = service.set_preference(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            preference_type="notification",
            key=event_type,
            value=pref_schema.model_dump(),
        )
        updated[event_type] = result["value"]

    return StandardResponse(
        data=updated,
        message="Notification preferences updated successfully",
    )


@router.get(
    "/views/{module}",
    response_model=StandardListResponse[SavedViewResponse],
    status_code=status.HTTP_200_OK,
    summary="Get saved views",
    description="Get saved views for a module. Requires preferences.view permission.",
)
async def get_saved_views(
    current_user: Annotated[User, Depends(require_permission("preferences.view"))],
    views_service: Annotated[ViewsService, Depends(get_views_service)],
    module: str = Path(..., description="Module name"),
) -> StandardListResponse[SavedViewResponse]:
    """Get saved views for a module."""
    views = views_service.get_views(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        module=module,
    )

    return StandardListResponse(
        data=[SavedViewResponse(**view) for view in views],
        meta={
            "total": len(views),
            "page": 1,
            "page_size": max(len(views), 1),  # Minimum page_size is 1
            "total_pages": 1,
        },
    )


@router.post(
    "/views/{module}",
    response_model=StandardResponse[SavedViewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save a view",
    description="Save a view for a module. Requires preferences.manage permission.",
)
async def save_view(
    current_user: Annotated[User, Depends(require_permission("preferences.manage"))],
    views_service: Annotated[ViewsService, Depends(get_views_service)],
    module: str = Path(..., description="Module name"),
    view_data: SavedViewCreate = ...,
) -> StandardResponse[SavedViewResponse]:
    """Save a view."""
    view = views_service.save_view(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        module=module,
        name=view_data.name,
        config=view_data.config,
        is_default=view_data.is_default,
    )

    return StandardResponse(
        data=SavedViewResponse(**view),
        message="View saved successfully",
    )


@router.get(
    "/dashboards",
    response_model=StandardListResponse[DashboardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get dashboards",
    description="Get dashboards for the current user. Requires preferences.view permission.",
)
async def get_dashboards(
    current_user: Annotated[User, Depends(require_permission("preferences.view"))],
    dashboards_service: Annotated[DashboardsService, Depends(get_dashboards_service)],
) -> StandardListResponse[DashboardResponse]:
    """Get dashboards for the current user."""
    dashboards = dashboards_service.get_dashboards(
        user_id=current_user.id, tenant_id=current_user.tenant_id
    )

    return StandardListResponse(
        data=[DashboardResponse(**dashboard) for dashboard in dashboards],
        total=len(dashboards),
        page=1,
        page_size=len(dashboards),
        total_pages=1,
        message="Dashboards retrieved successfully",
    )


@router.post(
    "/dashboards",
    response_model=StandardResponse[DashboardResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create dashboard",
    description="Create a dashboard. Requires preferences.manage permission.",
)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    current_user: Annotated[User, Depends(require_permission("preferences.manage"))],
    dashboards_service: Annotated[DashboardsService, Depends(get_dashboards_service)],
) -> StandardResponse[DashboardResponse]:
    """Create a dashboard."""
    dashboard = dashboards_service.create_dashboard(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        name=dashboard_data.name,
        widgets=dashboard_data.widgets,
        is_default=dashboard_data.is_default,
    )

    return StandardResponse(
        data=DashboardResponse(**dashboard),
        message="Dashboard created successfully",
    )

