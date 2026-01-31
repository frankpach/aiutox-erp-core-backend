from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.tasks.routers.tasks_analytics import router

"""Tests for tasks statistics API endpoints."""




class TestTasksStatisticsAPI:
    """Test cases for tasks statistics API endpoints."""

    def setup_method(self):
        """Setup test data."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1/tasks", tags=["tasks-statistics"])
        self.client = TestClient(self.app)

        self.test_user = User(
            id="user-1",
            email="test@example.com",
            tenant_id="tenant-1"
        )

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
            "overdue_tasks": 5
        }

    @pytest.fixture
    def sample_trends(self):
        """Sample trends data."""
        return {
            "period": "30d",
            "data_points": [
                {"period": "2026-01-25", "created": 5, "completed": 3},
                {"period": "2026-01-26", "created": 3, "completed": 4},
                {"period": "2026-01-27", "created": 7, "completed": 2}
            ]
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
                "avg_time_in_state_hours": 24.5
            },
            {
                "state_id": "status-2",
                "state_name": "Llamado",
                "state_type": "in_progress",
                "state_color": "#2196F3",
                "task_count": 10,
                "avg_time_in_state_hours": None
            }
        ]

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_get_tasks_statistics_overview_success(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_statistics,
        mock_db_session
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
        assert "message" in data
        assert data["error"] is None
        assert data["message"] == "Tasks statistics retrieved successfully"

        # Verify statistics data
        stats_data = data["data"]
        assert stats_data["total_tasks"] == 100
        assert stats_data["completion_rate"] == 30.0
        assert stats_data["by_status"]["todo"] == 40

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_get_tasks_statistics_overview_with_filters(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_statistics,
        mock_db_session
    ):
        """Test statistics overview with date filters."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = sample_statistics

        # Make request with filters
        date_from = (datetime.utcnow() - timedelta(days=30)).isoformat()
        date_to = datetime.utcnow().isoformat()

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

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_get_tasks_trends_success(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_trends,
        mock_db_session
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
        assert data["message"] == "Tasks trends retrieved successfully"

        # Verify trends data
        trends_data = data["data"]
        assert trends_data["period"] == "30d"
        assert len(trends_data["data_points"]) == 3
        assert trends_data["data_points"][0]["created"] == 5
        assert trends_data["data_points"][0]["completed"] == 3

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_get_tasks_trends_default_period(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_trends,
        mock_db_session
    ):
        """Test trends retrieval with default period."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_trends.return_value = sample_trends

        # Make request without period parameter
        response = self.client.get("/api/v1/tasks/statistics/trends")

        # Verify response
        assert response.status_code == 200

        # Verify default period was used
        mock_data_source.get_trends.assert_called_once_with("30d", "tenant-1")

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_get_custom_states_metrics_success(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        sample_custom_metrics,
        mock_db_session
    ):
        """Test successful custom states metrics retrieval."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

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
        assert data["message"] == "Custom states metrics retrieved successfully"

        # Verify metrics data
        metrics_data = data["data"]
        assert len(metrics_data) == 2

        first_metric = metrics_data[0]
        assert first_metric["state_id"] == "status-1"
        assert first_metric["state_name"] == "Vendido"
        assert first_metric["task_count"] == 15
        assert first_metric["avg_time_in_state_hours"] == 24.5

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    def test_statistics_endpoints_permission_check(self, mock_require_permission):
        """Test that endpoints require proper permissions."""
        # Mock permission check to raise exception
        from app.core.exceptions import APIException

        mock_require_permission.side_effect = APIException(
            code="PERMISSION_DENIED",
            message="Insufficient permissions",
            status_code=403
        )

        # Test statistics overview endpoint
        response = self.client.get("/api/v1/tasks/statistics/overview")
        assert response.status_code == 403

        # Test trends endpoint
        response = self.client.get("/api/v1/tasks/statistics/trends")
        assert response.status_code == 403

        # Test custom states endpoint
        response = self.client.get("/api/v1/tasks/statistics/custom-states")
        assert response.status_code == 403

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_multi_tenancy_enforcement(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        mock_db_session
    ):
        """Test that tenant filtering is enforced."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.return_value = mock_db_session

        mock_data_source = Mock()
        mock_data_source_class.return_value = mock_data_source
        mock_data_source.get_statistics.return_value = {"total_tasks": 0}
        mock_data_source.get_trends.return_value = {"period": "30d", "data_points": []}
        mock_data_source.get_custom_states_metrics.return_value = []

        # Test statistics overview
        self.client.get("/api/v1/tasks/statistics/overview")

        # Verify data source was initialized with correct tenant ID
        mock_data_source_class.assert_called_with(mock_db_session, "tenant-1")

        # Verify tenant ID was passed to methods
        mock_data_source.get_statistics.assert_called()
        stats_call_args = mock_data_source.get_statistics.call_args
        assert stats_call_args[0][1] == "tenant-1"  # Second argument should be tenant_id

    def test_response_format_compliance(self):
        """Test that responses follow the standard API contract."""
        from app.core.exceptions import APIException

        # Mock permission to raise exception to test error response
        with patch('app.modules.tasks.routers.tasks_analytics.require_permission') as mock_perm:
            mock_perm.side_effect = APIException(
                code="TEST_ERROR",
                message="Test error message",
                status_code=400
            )

            response = self.client.get("/api/v1/tasks/statistics/overview")

            # Verify error response format
            assert response.status_code == 400
            data = response.json()
            assert "data" in data
            assert "error" in data
            assert data["data"] is None
            assert data["error"] is not None
            assert data["error"]["code"] == "TEST_ERROR"

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    def test_database_error_handling(
        self,
        mock_get_db,
        mock_require_permission
    ):
        """Test handling of database errors."""
        # Setup mocks
        mock_require_permission.return_value = lambda: self.test_user
        mock_get_db.side_effect = Exception("Database connection failed")

        # Make request
        response = self.client.get("/api/v1/tasks/statistics/overview")

        # Should return 500 error
        assert response.status_code == 500

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

    @patch('app.modules.tasks.routers.tasks_analytics.require_permission')
    @patch('app.modules.tasks.routers.tasks_analytics.get_db')
    @patch('app.modules.tasks.routers.tasks_analytics.TasksDataSource')
    def test_empty_data_handling(
        self,
        mock_data_source_class,
        mock_get_db,
        mock_require_permission,
        mock_db_session
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
            "overdue_tasks": 0
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
