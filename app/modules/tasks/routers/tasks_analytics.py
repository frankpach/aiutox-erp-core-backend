"""Task analytics endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.common import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/analytics/adoption",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get feature adoption metrics",
    description="Get adoption metrics for task features. Requires tasks.manage permission.",
)
async def get_adoption_metrics(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """Get feature adoption metrics."""
    from app.analytics.task_adoption import get_task_adoption_analytics

    analytics = get_task_adoption_analytics(db)
    metrics = analytics.get_feature_adoption(current_user.tenant_id)

    return StandardResponse(
        data=metrics,
        message="Adoption metrics retrieved successfully",
    )


@router.get(
    "/analytics/trends",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get adoption trends",
    description="Get adoption trends over time. Requires tasks.manage permission.",
)
async def get_adoption_trends(
    current_user: Annotated[User, Depends(require_permission("tasks.manage"))],
    db: Annotated[Session, Depends(get_db)],
    days: int = Query(30, description="Days to analyze"),
) -> StandardResponse[dict]:
    """Get adoption trends."""
    from app.analytics.task_adoption import get_task_adoption_analytics

    analytics = get_task_adoption_analytics(db)
    trends = analytics.get_adoption_trends(current_user.tenant_id, days)

    return StandardResponse(
        data=trends,
        message="Adoption trends retrieved successfully",
    )
