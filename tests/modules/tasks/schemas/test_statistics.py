"""Tests for tasks statistics schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.modules.tasks.schemas.statistics import (
    CustomStateMetrics,
    ProductivityKPI,
    StandardListResponse,
    StandardResponse,
    StatisticsRequest,
    TaskMetricsFilter,
    TasksStatisticsResponse,
    TasksTrendsResponse,
    TrendDataPoint,
    TrendsRequest,
)


class TestTasksStatisticsResponse:
    """Test cases for TasksStatisticsResponse schema."""

    def test_valid_statistics_response(self):
        """Test creating a valid statistics response."""
        data = {
            "total_tasks": 100,
            "by_status": {"todo": 40, "in_progress": 30, "done": 30},
            "by_priority": {"high": 20, "medium": 50, "low": 30},
            "by_custom_state": {"Vendido": 15, "Llamado": 10},
            "completion_rate": 30.0,
            "completed_tasks": 30,
            "overdue_tasks": 5
        }

        response = TasksStatisticsResponse(**data)

        assert response.total_tasks == 100
        assert response.completion_rate == 30.0
        assert response.by_status["todo"] == 40
        assert response.overdue_tasks == 5

    def test_missing_required_fields(self):
        """Test validation error with missing required fields."""
        data = {
            "total_tasks": 100,
            # Missing other required fields
        }

        with pytest.raises(ValidationError):
            TasksStatisticsResponse(**data)

    def test_invalid_data_types(self):
        """Test validation error with invalid data types."""
        data = {
            "total_tasks": "not_a_number",  # Should be int
            "by_status": {"todo": 40, "in_progress": 30, "done": 30},
            "by_priority": {"high": 20, "medium": 50, "low": 30},
            "by_custom_state": {"Vendido": 15, "Llamado": 10},
            "completion_rate": 30.0,
            "completed_tasks": 30,
            "overdue_tasks": 5
        }

        with pytest.raises(ValidationError):
            TasksStatisticsResponse(**data)

    def test_empty_statistics(self):
        """Test statistics response with empty data."""
        data = {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 0.0,
            "completed_tasks": 0,
            "overdue_tasks": 0
        }

        response = TasksStatisticsResponse(**data)

        assert response.total_tasks == 0
        assert response.completion_rate == 0.0
        assert len(response.by_status) == 0


class TestTrendDataPoint:
    """Test cases for TrendDataPoint schema."""

    def test_valid_trend_data_point(self):
        """Test creating a valid trend data point."""
        data = {
            "period": "2026-01-27",
            "created": 5,
            "completed": 3
        }

        point = TrendDataPoint(**data)

        assert point.period == "2026-01-27"
        assert point.created == 5
        assert point.completed == 3

    def test_missing_required_fields(self):
        """Test validation error with missing required fields."""
        data = {
            "period": "2026-01-27",
            # Missing created and completed
        }

        with pytest.raises(ValidationError):
            TrendDataPoint(**data)

    def test_negative_values(self):
        """Test handling of negative values."""
        data = {
            "period": "2026-01-27",
            "created": -1,  # Should be allowed (could represent deletions)
            "completed": 3
        }

        point = TrendDataPoint(**data)
        assert point.created == -1


class TestTasksTrendsResponse:
    """Test cases for TasksTrendsResponse schema."""

    def test_valid_trends_response(self):
        """Test creating a valid trends response."""
        data = {
            "period": "30d",
            "data_points": [
                {"period": "2026-01-25", "created": 5, "completed": 3},
                {"period": "2026-01-26", "created": 3, "completed": 4}
            ]
        }

        response = TasksTrendsResponse(**data)

        assert response.period == "30d"
        assert len(response.data_points) == 2
        assert response.data_points[0].created == 5

    def test_empty_data_points(self):
        """Test trends response with empty data points."""
        data = {
            "period": "7d",
            "data_points": []
        }

        response = TasksTrendsResponse(**data)

        assert response.period == "7d"
        assert len(response.data_points) == 0

    def test_invalid_period(self):
        """Test trends response with invalid period."""
        data = {
            "period": "",  # Empty string should be allowed
            "data_points": []
        }

        response = TasksTrendsResponse(**data)
        assert response.period == ""


class TestCustomStateMetrics:
    """Test cases for CustomStateMetrics schema."""

    def test_valid_custom_state_metrics(self):
        """Test creating valid custom state metrics."""
        data = {
            "state_id": "status-1",
            "state_name": "Vendido",
            "state_type": "closed",
            "state_color": "#FF5722",
            "task_count": 15,
            "avg_time_in_state_hours": 24.5
        }

        metrics = CustomStateMetrics(**data)

        assert metrics.state_id == "status-1"
        assert metrics.state_name == "Vendido"
        assert metrics.task_count == 15
        assert metrics.avg_time_in_state_hours == 24.5

    def test_null_average_time(self):
        """Test custom state metrics with null average time."""
        data = {
            "state_id": "status-2",
            "state_name": "Llamado",
            "state_type": "in_progress",
            "state_color": "#2196F3",
            "task_count": 10,
            "avg_time_in_state_hours": None
        }

        metrics = CustomStateMetrics(**data)
        assert metrics.avg_time_in_state_hours is None

    def test_invalid_color_format(self):
        """Test custom state metrics with invalid color format."""
        data = {
            "state_id": "status-1",
            "state_name": "Vendido",
            "state_type": "closed",
            "state_color": "invalid_color",  # Should be allowed (validation not enforced)
            "task_count": 15,
            "avg_time_in_state_hours": 24.5
        }

        metrics = CustomStateMetrics(**data)
        assert metrics.state_color == "invalid_color"


class TestTaskMetricsFilter:
    """Test cases for TaskMetricsFilter schema."""

    def test_empty_filter(self):
        """Test filter with all optional fields None."""
        filter_data = TaskMetricsFilter()

        assert filter_data.date_from is None
        assert filter_data.date_to is None
        assert filter_data.status is None
        assert filter_data.priority is None
        assert filter_data.assigned_to is None

    def test_filter_with_dates(self):
        """Test filter with date values."""
        date_from = datetime(2026, 1, 1)
        date_to = datetime(2026, 1, 31)

        filter_data = TaskMetricsFilter(
            date_from=date_from,
            date_to=date_to,
            status="todo",
            priority="high"
        )

        assert filter_data.date_from == date_from
        assert filter_data.date_to == date_to
        assert filter_data.status == "todo"
        assert filter_data.priority == "high"


class TestProductivityKPI:
    """Test cases for ProductivityKPI schema."""

    def test_valid_kpi(self):
        """Test creating a valid KPI."""
        data = {
            "title": "Total Tasks",
            "value": 100,
            "format": "number",
            "icon": "tasks",
            "color": "#3B82F6",
            "trend": 5.2
        }

        kpi = ProductivityKPI(**data)

        assert kpi.title == "Total Tasks"
        assert kpi.value == 100
        assert kpi.format == "number"
        assert kpi.icon == "tasks"
        assert kpi.trend == 5.2

    def test_kpi_minimal_fields(self):
        """Test KPI with only required fields."""
        data = {
            "title": "Completion Rate",
            "value": 85.5,
            "format": "percentage"
        }

        kpi = ProductivityKPI(**data)

        assert kpi.title == "Completion Rate"
        assert kpi.value == 85.5
        assert kpi.format == "percentage"
        assert kpi.icon is None
        assert kpi.color is None
        assert kpi.trend is None


class TestStandardResponse:
    """Test cases for StandardResponse schema."""

    def test_response_with_data(self):
        """Test standard response with data."""
        data = {
            "data": {"key": "value"},
            "error": None,
            "meta": {"timestamp": "2026-01-27T12:00:00Z"}
        }

        response = StandardResponse(**data)

        assert response.data == {"key": "value"}
        assert response.error is None
        assert response.meta["timestamp"] == "2026-01-27T12:00:00Z"

    def test_response_with_error(self):
        """Test standard response with error."""
        data = {
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data"
            },
            "meta": None
        }

        response = StandardResponse(**data)

        assert response.data is None
        assert response.error["code"] == "VALIDATION_ERROR"
        assert response.meta is None

    def test_minimal_response(self):
        """Test minimal standard response."""
        data = {
            "data": "simple_data",
            "error": None,
            "meta": {}
        }

        response = StandardResponse(**data)

        assert response.data == "simple_data"
        assert response.error is None
        assert response.meta == {}


class TestStandardListResponse:
    """Test cases for StandardListResponse schema."""

    def test_list_response_with_data(self):
        """Test standard list response with data."""
        data = {
            "data": [{"id": 1}, {"id": 2}],
            "error": None,
            "meta": {
                "total": 2,
                "page": 1,
                "page_size": 10
            }
        }

        response = StandardListResponse(**data)

        assert len(response.data) == 2
        assert response.data[0]["id"] == 1
        assert response.meta["total"] == 2

    def test_empty_list_response(self):
        """Test empty list response."""
        data = {
            "data": [],
            "error": None,
            "meta": {
                "total": 0,
                "page": 1,
                "page_size": 10
            }
        }

        response = StandardListResponse(**data)

        assert len(response.data) == 0
        assert response.meta["total"] == 0


class TestRequestSchemas:
    """Test cases for request schemas."""

    def test_statistics_request(self):
        """Test StatisticsRequest schema."""
        filter_data = TaskMetricsFilter(status="todo")
        request_data = StatisticsRequest(
            filters=filter_data,
            include_custom_states=True
        )

        assert request_data.filters.status == "todo"
        assert request_data.include_custom_states is True

    def test_trends_request(self):
        """Test TrendsRequest schema."""
        filter_data = TaskMetricsFilter(priority="high")
        request_data = TrendsRequest(
            period="7d",
            filters=filter_data
        )

        assert request_data.period == "7d"
        assert request_data.filters.priority == "high"

    def test_trends_request_default_period(self):
        """Test TrendsRequest with default period."""
        request_data = TrendsRequest()

        assert request_data.period == "30d"
        assert request_data.filters is None


class TestSchemaFieldValidation:
    """Test field validation across schemas."""

    def test_string_field_max_length(self):
        """Test string field length validation."""
        data = {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 0.0,
            "completed_tasks": 0,
            "overdue_tasks": 0
        }

        # This should work fine as no max_length is defined for string fields
        response = TasksStatisticsResponse(**data)
        assert response.total_tasks == 0

    def test_numeric_field_ranges(self):
        """Test numeric field ranges."""
        # Test with very large numbers
        data = {
            "total_tasks": 2**31,  # Large number
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 150.0,  # Over 100%
            "completed_tasks": 0,
            "overdue_tasks": 0
        }

        response = TasksStatisticsResponse(**data)
        assert response.total_tasks == 2**31
        assert response.completion_rate == 150.0

    def test_dict_field_structure(self):
        """Test dictionary field structure validation."""
        # Test with empty dict
        data = {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 0.0,
            "completed_tasks": 0,
            "overdue_tasks": 0
        }

        response = TasksStatisticsResponse(**data)
        assert isinstance(response.by_status, dict)
        assert len(response.by_status) == 0

    def test_list_field_validation(self):
        """Test list field validation."""
        # Test with empty list
        data = {
            "period": "30d",
            "data_points": []
        }

        response = TasksTrendsResponse(**data)
        assert isinstance(response.data_points, list)
        assert len(response.data_points) == 0
