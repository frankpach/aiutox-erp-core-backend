"""Task analytics endpoints."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.models.user import User
from app.schemas.common import StandardResponse

from ..reporting.data_source import TasksDataSource
from ..schemas.statistics import (
    CustomStateMetrics,
    TasksStatisticsResponse,
    TasksTrendsResponse,
)

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


@router.get(
    "/statistics/overview",
    response_model=StandardResponse[TasksStatisticsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tasks statistics overview",
    description="Get comprehensive statistics for tasks. Requires tasks.view permission.",
)
async def get_tasks_statistics_overview(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    date_from: datetime | None = Query(None, description="Start date filter"),
    date_to: datetime | None = Query(None, description="End date filter"),
    status: str | None = Query(None, description="Status filter"),
    priority: str | None = Query(None, description="Priority filter"),
) -> StandardResponse[TasksStatisticsResponse]:
    """Get tasks statistics overview."""
    # Create data source
    data_source = TasksDataSource(db, str(current_user.tenant_id))

    # Build filters
    filters = {}
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority

    # Get statistics
    statistics = data_source.get_statistics(filters, str(current_user.tenant_id))

    # Convert to response model
    response_data = TasksStatisticsResponse(**statistics)

    return StandardResponse(
        data=response_data,
        message="Tasks statistics retrieved successfully",
    )


@router.get(
    "/statistics/trends",
    response_model=StandardResponse[TasksTrendsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tasks trends",
    description="Get task creation and completion trends over time. Requires tasks.view permission.",
)
async def get_tasks_trends(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
    period: str = Query("30d", description="Analysis period (7d, 30d, 90d)"),
) -> StandardResponse[TasksTrendsResponse]:
    """Get tasks trends."""
    # Create data source
    data_source = TasksDataSource(db, str(current_user.tenant_id))

    # Get trends
    trends = data_source.get_trends(period, str(current_user.tenant_id))

    # Convert to response model
    response_data = TasksTrendsResponse(**trends)

    return StandardResponse(
        data=response_data,
        message="Tasks trends retrieved successfully",
    )


@router.get(
    "/statistics/custom-states",
    response_model=StandardResponse[list[CustomStateMetrics]],
    status_code=status.HTTP_200_OK,
    summary="Get custom states metrics",
    description="Get usage metrics for custom task states. Requires tasks.view permission.",
)
async def get_custom_states_metrics(
    current_user: Annotated[User, Depends(require_permission("tasks.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[list[CustomStateMetrics]]:
    """Get custom states metrics."""
    # Create data source
    data_source = TasksDataSource(db, str(current_user.tenant_id))

    # Get custom states metrics
    metrics = data_source.get_custom_states_metrics(str(current_user.tenant_id))

    # Convert to response models
    response_data = [CustomStateMetrics(**metric) for metric in metrics]

    return StandardResponse(
        data=response_data,
        message="Custom states metrics retrieved successfully",
    )
