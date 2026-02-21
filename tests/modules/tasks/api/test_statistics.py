from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, get_user_permissions
from app.models.user import User
from app.modules.tasks.routers.tasks_analytics import router

"""Tests for tasks statistics API endpoints."""


class TestTasksStatisticsAPI:
    """Test cases for tasks statistics API endpoints."""

    def setup_method(self):
        """Setup test data."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(
            router, prefix="/api/v1/tasks", tags=["tasks-statistics"]
        )

        self.test_tenant_id = UUID("00000000-0000-0000-0000-000000000001")
        self.test_user = User(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            email="test@example.com",
            tenant_id=self.test_tenant_id,
        )

        # Override auth dependencies so endpoints don't require a real JWT
        self.app.dependency_overrides[get_current_user] = lambda: self.test_user
        self.app.dependency_overrides[get_user_permissions] = lambda: {
            "tasks.manage",
            "tasks.view",
        }

        self.client = TestClient(self.app)

    def teardown_method(self):
        """Cleanup dependency overrides."""
        self.app.dependency_overrides.clear()

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_statistics(self):
        """Sample statistics data."""
        return {
            "total_tasks": 100,
            "by_status": {"todo": 40, "in_progress": 30, "done": 30},
            "by_priority": {"high": 20, "medium": 50, "low": 30},
            "by_custom_state": {"Vendido": 15, "Llamado": 10},
            "completion_rate": 30.0,
            "completed_tasks": 30,
            "overdue_tasks": 5,
        }

    @pytest.fixture
    def sample_trends(self):
        """Sample trends data."""
        return {
            "period": "30d",
            "data_points": [
                {"period": "2026-01-25", "created": 5, "completed": 3},
                {"period": "2026-01-26", "created": 3, "completed": 4},
                {"period": "2026-01-27", "created": 7, "completed": 2},
            ],
        }

    @pytest.fixture
    def sample_custom_metrics(self):
        """Sample custom state metrics."""
        return [
            {
                "state_id": "status-1",
                "state_name": "Vendido",
                "state_type": "closed",
                "state_color": "#FF5722",
                "task_count": 15,
                "avg_time_in_state_hours": 24.5,
            },
            {
                "state_id": "status-2",
                "state_name": "Llamado",
                "state_type": "in_progress",
                "state_color": "#2196F3",
                "task_count": 10,
                "avg_time_in_state_hours": None,
            },
        ]

    @patch("app.modules.tasks.routers.tasks_analytics.require_permission")
    @patch("app.modules.tasks.routers.tasks_analytics.get_db")
    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_get_tasks_statistics_overview_success(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_statistics,
        mock_db_session,
    ):
        """Test successful statistics overview retrieval."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = sample_statistics

        # Make request
        response = self.client.get("/api/v1/tasks/statistics/overview")

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert "error" in data
        assert data["error"] is None

        # Verify statistics data
        stats_data = data["data"]
        assert stats_data["total_tasks"] == 100
        assert stats_data["completion_rate"] == 30.0
        assert stats_data["by_status"]["todo"] == 40

    @patch("app.modules.tasks.routers.tasks_analytics.require_permission")
    @patch("app.modules.tasks.routers.tasks_analytics.get_db")
    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_get_tasks_statistics_overview_with_filters(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_statistics,
        mock_db_session,
    ):
        """Test statistics overview with date filters."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = sample_statistics

        # Make request with filters
        date_from = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        date_to = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")

        response = self.client.get(
            f"/api/v1/tasks/statistics/overview?date_from={date_from}&date_to={date_to}&status=todo&priority=high"
        )

        # Verify response
        assert response.status_code == 200

        # Verify data source was called with correct filters
        mock_data_source.get_statistics.assert_called_once()
        call_args = mock_data_source.get_statistics.call_args
        filters = call_args[0][0]  # First positional argument

        assert "date_from" in filters
        assert "date_to" in filters
        assert filters["status"] == "todo"
        assert filters["priority"] == "high"

    @patch("app.modules.tasks.routers.tasks_analytics.require_permission")
    @patch("app.modules.tasks.routers.tasks_analytics.get_db")
    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_get_tasks_trends_success(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_trends,
        mock_db_session,
    ):
        """Test successful trends retrieval."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_trends.return_value = sample_trends

        # Make request
        response = self.client.get("/api/v1/tasks/statistics/trends?period=30d")

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["error"] is None

        # Verify trends data
        trends_data = data["data"]
        assert trends_data["period"] == "30d"
        assert len(trends_data["data_points"]) == 3
        assert trends_data["data_points"][0]["created"] == 5
        assert trends_data["data_points"][0]["completed"] == 3

    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_get_tasks_trends_default_period(
        self,
        mock_data_source_class,
        sample_trends,
    ):
        """Test trends retrieval with default period."""
        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_trends.return_value = sample_trends

        # Make request without period parameter
        response = self.client.get("/api/v1/tasks/statistics/trends")

        # Verify response
        assert response.status_code == 200

        # Verify default period was used (tenant_id is the UUID string)
        tenant_id_str = str(self.test_tenant_id)
        mock_data_source.get_trends.assert_called_once_with("30d", tenant_id_str)

    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_get_custom_states_metrics_success(
        self,
        mock_data_source_class,
        sample_custom_metrics,
    ):
        """Test successful custom states metrics retrieval."""
        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_custom_states_metrics.return_value = sample_custom_metrics

        # Make request
        response = self.client.get("/api/v1/tasks/statistics/custom-states")

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["error"] is None

        # Verify metrics data
        metrics_data = data["data"]
        assert len(metrics_data) == 2

        first_metric = metrics_data[0]
        assert first_metric["state_id"] == "status-1"
        assert first_metric["state_name"] == "Vendido"
        assert first_metric["task_count"] == 15
        assert first_metric["avg_time_in_state_hours"] == 24.5

    def test_statistics_endpoints_permission_check(self):
        """Test that endpoints require proper permissions."""

        # Override get_user_permissions to return empty set (no permissions)
        def no_permissions():
            return set()

        self.app.dependency_overrides[get_user_permissions] = no_permissions

        # Test statistics overview endpoint
        response = self.client.get("/api/v1/tasks/statistics/overview")
        assert response.status_code == 403

        # Test trends endpoint
        response = self.client.get("/api/v1/tasks/statistics/trends")
        assert response.status_code == 403

        # Test custom states endpoint
        response = self.client.get("/api/v1/tasks/statistics/custom-states")
        assert response.status_code == 403

        # Restore full permissions for subsequent tests
        self.app.dependency_overrides[get_user_permissions] = lambda: {
            "tasks.manage",
            "tasks.view",
        }

    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_multi_tenancy_enforcement(self, mock_data_source_class, mock_db_session):
        """Test that tenant filtering is enforced."""
        tenant_id_str = str(self.test_tenant_id)

        full_stats = {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 0.0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
        }
        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = full_stats

        # Test statistics overview
        self.client.get("/api/v1/tasks/statistics/overview")

        # Verify tenant ID was passed to methods
        mock_data_source.get_statistics.assert_called()
        stats_call_args = mock_data_source.get_statistics.call_args
        assert stats_call_args[0][1] == tenant_id_str

    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_response_format_compliance(self, mock_data_source_class):
        """Test that responses follow the standard API contract."""
        from app.core.exceptions import APIException

        # Make TasksDataSource raise an APIException to test error response format
        mock_data_source_class.side_effect = APIException(
            code="TEST_ERROR", message="Test error message", status_code=400
        )

        response = self.client.get("/api/v1/tasks/statistics/overview")

        # Verify error response format — APIException is returned as {"detail": {"error": {...}}}
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"]["code"] == "TEST_ERROR"

    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_database_error_handling(self, mock_data_source_class):
        """Test handling of database errors."""
        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.side_effect = Exception(
            "Database connection failed"
        )

        # Make request — unhandled exceptions propagate as 500 in TestClient
        import pytest as _pytest

        with _pytest.raises(Exception, match="Database connection failed"):
            self.client.get("/api/v1/tasks/statistics/overview")

    def test_endpoint_paths_and_methods(self):
        """Test that endpoints are registered with correct paths and methods."""
        # Get all routes from the router
        routes = [route for route in router.routes if "statistics" in route.path]

        # Verify expected endpoints exist
        endpoint_paths = [route.path for route in routes]
        assert "/statistics/overview" in endpoint_paths
        assert "/statistics/trends" in endpoint_paths
        assert "/statistics/custom-states" in endpoint_paths

        # Verify all are GET methods
        for route in routes:
            assert "GET" in route.methods

    @patch("app.modules.tasks.routers.tasks_analytics.require_permission")
    @patch("app.modules.tasks.routers.tasks_analytics.get_db")
    @patch("app.modules.tasks.routers.tasks_analytics.TasksDataSource")
    def test_empty_data_handling(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        mock_db_session,
    ):
        """Test handling of empty data responses."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = {
            "total_tasks": 0,
            "by_status": {},
            "by_priority": {},
            "by_custom_state": {},
            "completion_rate": 0.0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
        }
        mock_data_source.get_trends.return_value = {"period": "30d", "data_points": []}
        mock_data_source.get_custom_states_metrics.return_value = []

        # Test statistics overview with empty data
        response = self.client.get("/api/v1/tasks/statistics/overview")
        assert response.status_code == 200

        data = response.json()
        stats_data = data["data"]
        assert stats_data["total_tasks"] == 0
        assert stats_data["completion_rate"] == 0.0

        # Test trends with empty data
        response = self.client.get("/api/v1/tasks/statistics/trends")
        assert response.status_code == 200

        data = response.json()
        trends_data = data["data"]
        assert len(trends_data["data_points"]) == 0

        # Test custom states with empty data
        response = self.client.get("/api/v1/tasks/statistics/custom-states")
        assert response.status_code == 200

        data = response.json()
        metrics_data = data["data"]
        assert len(metrics_data) == 0
