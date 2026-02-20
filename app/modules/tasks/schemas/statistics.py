from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

"""Pydantic schemas for tasks statistics and reporting."""


class TasksStatisticsResponse(BaseModel):
    """Response schema for tasks statistics overview."""

    total_tasks: int = Field(..., description="Total number of tasks")
    by_status: dict[str, int] = Field(..., description="Tasks grouped by status")
    by_priority: dict[str, int] = Field(..., description="Tasks grouped by priority")
    by_custom_state: dict[str, int] = Field(
        ..., description="Tasks grouped by custom state"
    )
    completion_rate: float = Field(..., description="Completion rate percentage")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    overdue_tasks: int = Field(..., description="Number of overdue tasks")

    model_config = ConfigDict(from_attributes=True)


class TrendDataPoint(BaseModel):
    """Single data point for trend analysis."""

    period: str = Field(..., description="Time period (date/week)")
    created: int = Field(..., description="Number of tasks created")
    completed: int = Field(..., description="Number of tasks completed")

    model_config = ConfigDict(from_attributes=True)


class TasksTrendsResponse(BaseModel):
    """Response schema for tasks trends analysis."""

    period: str = Field(..., description="Analysis period (7d, 30d, 90d)")
    data_points: list[TrendDataPoint] = Field(..., description="Trend data points")

    model_config = ConfigDict(from_attributes=True)


class CustomStateMetrics(BaseModel):
    """Metrics for custom task states."""

    state_id: str = Field(..., description="State ID")
    state_name: str = Field(..., description="State name")
    state_type: str = Field(..., description="State type (open, in_progress, closed)")
    state_color: str = Field(..., description="State color hex code")
    task_count: int = Field(..., description="Number of tasks in this state")
    avg_time_in_state_hours: float | None = Field(
        ..., description="Average time in state (hours)"
    )

    model_config = ConfigDict(from_attributes=True)


class TasksOverviewResponse(BaseModel):
    """Comprehensive tasks overview with multiple metrics."""

    statistics: TasksStatisticsResponse = Field(..., description="Basic statistics")
    recent_trends: TasksTrendsResponse = Field(..., description="Recent trends (7d)")
    custom_states: list[CustomStateMetrics] = Field(
        ..., description="Custom state metrics"
    )

    model_config = ConfigDict(from_attributes=True)


class TaskMetricsFilter(BaseModel):
    """Filter parameters for task metrics queries."""

    date_from: datetime | None = Field(None, description="Start date filter")
    date_to: datetime | None = Field(None, description="End date filter")
    status: str | None = Field(None, description="Status filter")
    priority: str | None = Field(None, description="Priority filter")
    assigned_to: str | None = Field(None, description="Assigned user filter")

    model_config = ConfigDict(from_attributes=True)


class ProductivityKPI(BaseModel):
    """Individual KPI for productivity metrics."""

    title: str = Field(..., description="KPI title")
    value: float | int = Field(..., description="KPI value")
    format: str = Field(..., description="Value format (number, percentage, hours)")
    icon: str | None = Field(None, description="Icon name")
    color: str | None = Field(None, description="Display color")
    trend: float | None = Field(None, description="Trend percentage")

    model_config = ConfigDict(from_attributes=True)


class ProductivityMetricsResponse(BaseModel):
    """Response schema for productivity metrics."""

    kpis: list[ProductivityKPI] = Field(..., description="Productivity KPIs")
    period: str = Field(..., description="Analysis period")
    generated_at: datetime = Field(..., description="When metrics were generated")

    model_config = ConfigDict(from_attributes=True)


class TasksByPriorityResponse(BaseModel):
    """Response schema for tasks grouped by priority."""

    total_tasks: int = Field(..., description="Total tasks")
    by_priority: dict[str, int] = Field(..., description="Tasks by priority")
    priority_distribution: dict[str, float] = Field(
        ..., description="Priority distribution percentages"
    )

    model_config = ConfigDict(from_attributes=True)


class TaskCompletionTimeline(BaseModel):
    """Single point in task completion timeline."""

    date: str = Field(..., description="Completion date")
    task_id: str = Field(..., description="Task ID")
    task_title: str = Field(..., description="Task title")
    priority: str = Field(..., description="Task priority")
    completion_time_hours: float | None = Field(
        None, description="Time to complete (hours)"
    )

    model_config = ConfigDict(from_attributes=True)


class TaskCompletionTimelineResponse(BaseModel):
    """Response schema for task completion timeline."""

    period: str = Field(..., description="Analysis period")
    timeline: list[TaskCompletionTimeline] = Field(
        ..., description="Completion timeline"
    )
    avg_completion_time: float | None = Field(
        None, description="Average completion time (hours)"
    )
    total_completed: int = Field(..., description="Total completed tasks")

    model_config = ConfigDict(from_attributes=True)


# Request schemas for API endpoints
class StatisticsRequest(BaseModel):
    """Request schema for statistics endpoints."""

    filters: TaskMetricsFilter | None = Field(None, description="Filter parameters")
    include_custom_states: bool = Field(
        True, description="Include custom state metrics"
    )

    model_config = ConfigDict(from_attributes=True)


class TrendsRequest(BaseModel):
    """Request schema for trends endpoints."""

    period: str = Field("30d", description="Analysis period (7d, 30d, 90d)")
    filters: TaskMetricsFilter | None = Field(None, description="Filter parameters")

    model_config = ConfigDict(from_attributes=True)


# Response wrapper schemas following API contract
class StandardResponse(BaseModel):
    """Standard API response wrapper."""

    data: Any | None = Field(None, description="Response data")
    error: dict[str, Any] | None = Field(None, description="Error information")
    meta: dict[str, Any] | None = Field(None, description="Metadata")

    model_config = ConfigDict(from_attributes=True)


class StandardListResponse(BaseModel):
    """Standard list API response wrapper."""

    data: list[Any] = Field(..., description="Response data list")
    error: dict[str, Any] | None = Field(None, description="Error information")
    meta: dict[str, Any] = Field(..., description="Pagination/metadata")

    model_config = ConfigDict(from_attributes=True)
