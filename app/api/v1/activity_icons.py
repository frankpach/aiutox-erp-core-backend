"""
Activity Icon Configuration API Endpoints
Provides endpoints for managing activity icon configurations
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.activity_icon_config import ActivityIconConfig
from app.models.user import User
from app.schemas.activity_icon import (
    ActivityIconConfigBulkUpdate,
    ActivityIconConfigCreate,
    ActivityIconConfigResponse,
    ActivityIconConfigUpdate,
)

router = APIRouter(prefix="/activity-icons", tags=["activity-icons"])


# Default icon configurations
DEFAULT_ICONS = {
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


@router.get("/", response_model=dict[str, Any])
async def get_activity_icons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get activity icon configurations for the current tenant.
    Returns custom configurations or defaults if none exist.
    """
    tenant_id = current_user.tenant_id

    # Query all icon configs for this tenant
    stmt = select(ActivityIconConfig).where(
        ActivityIconConfig.tenant_id == tenant_id,
        ActivityIconConfig.is_active == True,  # noqa: E712
    )
    result = db.execute(stmt)
    configs = result.scalars().all()

    # If no custom configs exist, return defaults
    if not configs:
        return {"data": []}

    # Convert to response format
    response_data = [
        ActivityIconConfigResponse.model_validate(config)
        for config in configs
    ]

    return {"data": response_data}


@router.get("/defaults", response_model=dict[str, Any])
async def get_default_icons() -> dict[str, Any]:
    """
    Get default icon configurations.
    This endpoint doesn't require authentication as it returns static defaults.
    """
    return {"data": DEFAULT_ICONS}


@router.post("/", response_model=dict[str, Any])
async def create_activity_icon(
    icon_config: ActivityIconConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Create a new activity icon configuration.
    """
    tenant_id = current_user.tenant_id

    # Check if config already exists
    stmt = select(ActivityIconConfig).where(
        ActivityIconConfig.tenant_id == tenant_id,
        ActivityIconConfig.activity_type == icon_config.activity_type,
        ActivityIconConfig.status == icon_config.status,
    )
    result = db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise APIException(
            status_code=409,
            error_code="ICON_CONFIG_EXISTS",
            message=f"Icon configuration already exists for {icon_config.activity_type}/{icon_config.status}",
        )

    # Create new config
    new_config = ActivityIconConfig(
        tenant_id=tenant_id,
        activity_type=icon_config.activity_type,
        status=icon_config.status,
        icon=icon_config.icon,
        class_name=icon_config.class_name,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    return {"data": ActivityIconConfigResponse.model_validate(new_config)}


@router.put("/bulk", response_model=dict[str, Any])
async def bulk_update_activity_icons(
    bulk_update: ActivityIconConfigBulkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Bulk update activity icon configurations.
    Creates or updates multiple icon configurations at once.
    """
    tenant_id = current_user.tenant_id
    updated_configs = []

    for activity_type, statuses in bulk_update.configs.items():
        for status, icon in statuses.items():
            # Check if config exists
            stmt = select(ActivityIconConfig).where(
                ActivityIconConfig.tenant_id == tenant_id,
                ActivityIconConfig.activity_type == activity_type,
                ActivityIconConfig.status == status,
            )
            result = db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.icon = icon
                existing.updated_at = datetime.utcnow()
                updated_configs.append(existing)
            else:
                # Create new
                new_config = ActivityIconConfig(
                    tenant_id=tenant_id,
                    activity_type=activity_type,
                    status=status,
                    icon=icon,
                    class_name=DEFAULT_ICONS.get(activity_type, {}).get(status, {}).get("class_name"),
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(new_config)
                updated_configs.append(new_config)

    db.commit()

    # Refresh all configs
    for config in updated_configs:
        db.refresh(config)

    response_data = [
        ActivityIconConfigResponse.model_validate(config)
        for config in updated_configs
    ]

    return {"data": response_data}


@router.put("/{config_id}", response_model=dict[str, Any])
async def update_activity_icon(
    config_id: UUID,
    icon_update: ActivityIconConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Update an existing activity icon configuration.
    """
    tenant_id = current_user.tenant_id

    # Get existing config
    stmt = select(ActivityIconConfig).where(
        ActivityIconConfig.id == config_id,
        ActivityIconConfig.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise APIException(
            status_code=404,
            error_code="ICON_CONFIG_NOT_FOUND",
            message="Icon configuration not found",
        )

    # Update fields
    update_data = icon_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    return {"data": ActivityIconConfigResponse.model_validate(config)}


@router.delete("/{config_id}", response_model=dict[str, Any])
async def delete_activity_icon(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Delete (soft delete) an activity icon configuration.
    """
    tenant_id = current_user.tenant_id

    # Get existing config
    stmt = select(ActivityIconConfig).where(
        ActivityIconConfig.id == config_id,
        ActivityIconConfig.tenant_id == tenant_id,
    )
    result = db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise APIException(
            status_code=404,
            error_code="ICON_CONFIG_NOT_FOUND",
            message="Icon configuration not found",
        )

    # Soft delete
    config.is_active = False
    config.updated_at = datetime.utcnow()

    db.commit()

    return {"data": {"message": "Icon configuration deleted successfully"}}
