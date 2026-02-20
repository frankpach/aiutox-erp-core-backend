"""Tests for tasks reporting registry."""

from unittest.mock import Mock, patch
from uuid import uuid4

from app.core.reporting.engine import ReportingEngine
from app.modules.tasks.reporting.registry import (
    create_default_reports,
    get_available_widgets,
    get_tasks_report_definitions,
    register_tasks_data_sources,
    validate_widget_config,
)


class TestTasksReportingRegistry:
    """Test suite for tasks reporting registry."""

    def test_get_tasks_report_definitions(self):
        """Test getting all tasks report definitions."""
        definitions = get_tasks_report_definitions()

        assert isinstance(definitions, dict)
        assert len(definitions) == 6

        # Check all expected report IDs are present
        expected_ids = [
            "tasks_by_status",
            "tasks_trends",
            "custom_states_usage",
            "productivity_metrics",
            "tasks_by_priority",
            "task_completion_timeline",
        ]

        for report_id in expected_ids:
            assert report_id in definitions
            assert hasattr(definitions[report_id], "name")
            assert hasattr(definitions[report_id], "data_source_type")
            assert hasattr(definitions[report_id], "visualization_type")

    def test_register_tasks_data_sources(self):
        """Test registration of tasks data sources."""
        from app.modules.tasks.reporting.data_source import TasksDataSource

        # Create mock engine
        mock_engine = Mock(spec=ReportingEngine)
        mock_engine.register_data_source = Mock()

        # Register data sources
        register_tasks_data_sources(mock_engine)

        # Verify registration was called with correct arguments
        mock_engine.register_data_source.assert_called_once_with(
            "tasks", TasksDataSource
        )

    @patch("app.core.reporting.service.ReportingService")
    @patch("app.modules.tasks.reporting.registry.ReportingEngine")
    def test_create_default_reports_success(
        self, mock_engine_class, mock_service_class
    ):
        """Test successful creation of default reports."""
        # Setup mocks
        mock_db = Mock()
        tenant_id = uuid4()
        created_by = uuid4()

        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock report creation
        mock_report = Mock()
        mock_report.id = uuid4()
        mock_service.create_report.return_value = mock_report

        # Create default reports
        report_ids = create_default_reports(mock_db, tenant_id, created_by)

        # Verify engine and service were initialized
        mock_engine_class.assert_called_once_with(mock_db)
        mock_service_class.assert_called_once_with(mock_db)

        # Verify data sources were registered
        mock_engine.register_data_source.assert_called_once()

        # Verify reports were created (should be 6 reports)
        assert mock_service.create_report.call_count == 6
        assert len(report_ids) == 6

        # Verify specific report calls
        call_args_list = mock_service.create_report.call_args_list
        report_names = [call.kwargs["name"] for call in call_args_list]

        expected_names = [
            "Tasks by Status",
            "Tasks Trends",
            "Tasks by Priority",
            "Custom States Usage",
            "Productivity Metrics",
            "Task Completion Timeline",
        ]

        for name in expected_names:
            assert name in report_names

    @patch("app.core.reporting.service.ReportingService")
    @patch("app.modules.tasks.reporting.registry.ReportingEngine")
    def test_create_default_reports_partial_failure(
        self, mock_engine_class, mock_service_class
    ):
        """Test creation of default reports with some failures."""
        # Setup mocks
        mock_db = Mock()
        tenant_id = uuid4()
        created_by = uuid4()

        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock report creation - fail on second call
        mock_report = Mock()
        mock_report.id = uuid4()
        mock_service.create_report.side_effect = [
            mock_report,  # First succeeds
            Exception("Database error"),  # Second fails
            mock_report,  # Third succeeds
            mock_report,  # Fourth succeeds
            mock_report,  # Fifth succeeds
            mock_report,  # Sixth succeeds
        ]

        # Create default reports - should not raise exception
        report_ids = create_default_reports(mock_db, tenant_id, created_by)

        # Should have 5 successful reports (one failed)
        assert len(report_ids) == 5
        assert mock_service.create_report.call_count == 6

    def test_get_available_widgets(self):
        """Test getting available widgets."""
        tenant_id = uuid4()
        widgets = get_available_widgets(tenant_id)

        assert isinstance(widgets, list)
        assert len(widgets) == 6

        # Check widget structure
        for widget in widgets:
            assert "widget_id" in widget
            assert "name" in widget
            assert "description" in widget
            assert "data_source_type" in widget
            assert "visualization_type" in widget
            assert "default_filters" in widget
            assert "default_config" in widget
            assert "category" in widget

            # Verify values
            assert widget["data_source_type"] == "tasks"
            assert widget["category"] == "tasks"
            assert isinstance(widget["default_filters"], dict)
            assert isinstance(widget["default_config"], dict)

        # Check specific widgets exist
        widget_ids = [w["widget_id"] for w in widgets]
        expected_ids = [
            "tasks_by_status",
            "tasks_trends",
            "custom_states_usage",
            "productivity_metrics",
            "tasks_by_priority",
            "task_completion_timeline",
        ]

        for widget_id in expected_ids:
            assert widget_id in widget_ids

    def test_validate_widget_config_valid(self):
        """Test validation of valid widget configurations."""
        # Test pie chart config
        pie_config = {"data_field": "by_status"}
        assert validate_widget_config("tasks_by_status", pie_config) is True

        # Test line chart config
        line_config = {
            "data_field": "data_points",
            "x_axis": "period",
            "y_axis": ["created", "completed"],
        }
        assert validate_widget_config("tasks_trends", line_config) is True

        # Test bar chart config
        bar_config = {
            "data_field": "task_count",
            "x_axis": "state_name",
            "y_axis": "task_count",
        }
        assert validate_widget_config("custom_states_usage", bar_config) is True

        # Test KPI config
        kpi_config = {
            "kpis": [{"title": "Total Tasks", "value": 100, "format": "number"}]
        }
        assert validate_widget_config("productivity_metrics", kpi_config) is True

        # Test timeline config
        timeline_config = {
            "data_field": "completed_tasks",
            "time_field": "completed_at",
        }
        assert (
            validate_widget_config("task_completion_timeline", timeline_config) is True
        )

    def test_validate_widget_config_invalid_widget_id(self):
        """Test validation with invalid widget ID."""
        config = {"data_field": "by_status"}
        assert validate_widget_config("nonexistent_widget", config) is False

    def test_validate_widget_config_invalid_config_pie(self):
        """Test validation of invalid pie chart configuration."""
        # Missing data_field
        config = {"chart_type": "pie"}
        assert validate_widget_config("tasks_by_status", config) is False

    def test_validate_widget_config_invalid_config_line(self):
        """Test validation of invalid line chart configuration."""
        # Missing y_axis
        config = {"data_field": "data_points", "x_axis": "period"}
        assert validate_widget_config("tasks_trends", config) is False

    def test_validate_widget_config_invalid_config_kpi(self):
        """Test validation of invalid KPI configuration."""
        # kpis not a list
        config = {"kpis": "not_a_list"}
        assert validate_widget_config("productivity_metrics", config) is False

    def test_validate_widget_config_invalid_config_timeline(self):
        """Test validation of invalid timeline configuration."""
        # Missing time_field
        config = {"data_field": "completed_tasks"}
        assert validate_widget_config("task_completion_timeline", config) is False

    def test_widget_config_structure(self):
        """Test that widget configurations have correct structure."""
        tenant_id = uuid4()
        widgets = get_available_widgets(tenant_id)

        for widget in widgets:
            # Verify required fields exist and have correct types
            assert isinstance(widget["widget_id"], str)
            assert isinstance(widget["name"], str)
            assert isinstance(widget["description"], str)
            assert isinstance(widget["data_source_type"], str)
            assert isinstance(widget["visualization_type"], str)
            assert isinstance(widget["default_filters"], dict)
            assert isinstance(widget["default_config"], dict)
            assert isinstance(widget["category"], str)

            # Verify no empty required fields
            assert widget["widget_id"]
            assert widget["name"]
            assert widget["data_source_type"]
            assert widget["visualization_type"]
            assert widget["category"]

    def test_report_definitions_consistency(self):
        """Test that report definitions are consistent with available widgets."""
        definitions = get_tasks_report_definitions()
        tenant_id = uuid4()
        widgets = get_available_widgets(tenant_id)

        # Should have same number of items
        assert len(definitions) == len(widgets)

        # All widget IDs should match report definition keys
        widget_ids = {w["widget_id"] for w in widgets}
        definition_ids = set(definitions.keys())

        assert widget_ids == definition_ids

        # Widget properties should match report definition properties
        for widget in widgets:
            report_def = definitions[widget["widget_id"]]
            assert widget["name"] == report_def.name
            assert widget["description"] == report_def.description
            assert widget["data_source_type"] == report_def.data_source_type
            assert widget["visualization_type"] == report_def.visualization_type
