"""Task preferences endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.models.user import User
from app.schemas.common import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/preferences/calendar",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get user calendar preferences",
    description="Get current user's calendar preferences. Requires tasks.view permission.",
)
async def get_calendar_preferences(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get user calendar preferences."""
    from app.models.user_calendar_preferences import UserCalendarPreferences

    prefs = (
        db.query(UserCalendarPreferences)
        .filter(UserCalendarPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        # Crear preferencias por defecto
        prefs = UserCalendarPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return StandardResponse(
        data={
            "id": str(prefs.id),
            "user_id": str(prefs.user_id),
            "auto_sync_enabled": prefs.auto_sync_enabled,
            "default_calendar_provider": prefs.default_calendar_provider,
            "timezone": prefs.timezone,
            "time_format": prefs.time_format,
        },
        message="Calendar preferences retrieved successfully",
    )


@router.put(
    "/preferences/calendar",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update user calendar preferences",
    description="Update current user's calendar preferences. Requires tasks.view permission.",
)
async def update_calendar_preferences(
    preferences: dict,
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Update user calendar preferences."""
    from app.models.user_calendar_preferences import UserCalendarPreferences

    prefs = (
        db.query(UserCalendarPreferences)
        .filter(UserCalendarPreferences.user_id == current_user.id)
        .first()
    )

    if not prefs:
        prefs = UserCalendarPreferences(user_id=current_user.id)
        db.add(prefs)

    # Actualizar campos
    for key, value in preferences.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)

    db.commit()
    db.refresh(prefs)

    return StandardResponse(
        data={
            "id": str(prefs.id),
            "user_id": str(prefs.user_id),
            "auto_sync_enabled": prefs.auto_sync_enabled,
            "default_calendar_provider": prefs.default_calendar_provider,
            "timezone": prefs.timezone,
            "time_format": prefs.time_format,
        },
        message="Calendar preferences updated successfully",
    )
