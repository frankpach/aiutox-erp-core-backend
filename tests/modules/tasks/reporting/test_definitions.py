"""Tests for tasks report definitions."""

from app.modules.tasks.reporting.definitions import (
    CUSTOM_STATES_USAGE_REPORT,
    PRODUCTIVITY_METRICS_REPORT,
    TASK_COMPLETION_TIMELINE_REPORT,
    TASKS_BY_PRIORITY_REPORT,
    TASKS_BY_STATUS_REPORT,
    TASKS_REPORT_DEFINITIONS,
    TASKS_TRENDS_REPORT,
    get_report_definition,
    get_tasks_report_definitions,
    validate_report_config,
)


class TestTasksReportDefinitions:
    """Test cases for tasks report definitions."""

    def test_tasks_by_status_report_definition(self):
        """Test TASKS_BY_STATUS_REPORT definition."""
        report = TASKS_BY_STATUS_REPORT

        assert report.name == "Tasks by Status"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "pie_chart"
        assert "date_range" in report.filters
        assert report.config["chart_type"] == "pie"
        assert "data_field" in report.config
        assert report.config["data_field"] == "by_status"

    def test_tasks_trends_report_definition(self):
        """Test TASKS_TRENDS_REPORT definition."""
        report = TASKS_TRENDS_REPORT

        assert report.name == "Tasks Trends"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "line_chart"
        assert "period" in report.filters
        assert report.config["chart_type"] == "line"
        assert "x_axis" in report.config
        assert "y_axis" in report.config
        assert isinstance(report.config["y_axis"], list)

    def test_custom_states_usage_report_definition(self):
        """Test CUSTOM_STATES_USAGE_REPORT definition."""
        report = CUSTOM_STATES_USAGE_REPORT

        assert report.name == "Custom States Usage"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "bar_chart"
        assert "state_type" in report.filters
        assert report.config["chart_type"] == "bar"
        assert "data_field" in report.config
        assert "x_axis" in report.config
        assert "y_axis" in report.config

    def test_productivity_metrics_report_definition(self):
        """Test PRODUCTIVITY_METRICS_REPORT definition."""
        report = PRODUCTIVITY_METRICS_REPORT

        assert report.name == "Productivity Metrics"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "kpi"
        assert "date_range" in report.filters
        assert "kpis" in report.config
        assert isinstance(report.config["kpis"], list)
        assert len(report.config["kpis"]) == 4

        # Check KPI structure
        first_kpi = report.config["kpis"][0]
        assert "title" in first_kpi
        assert "data_field" in first_kpi
        assert "format" in first_kpi

    def test_tasks_by_priority_report_definition(self):
        """Test TASKS_BY_PRIORITY_REPORT definition."""
        report = TASKS_BY_PRIORITY_REPORT

        assert report.name == "Tasks by Priority"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "donut_chart"
        assert "status_filter" in report.filters
        assert report.config["chart_type"] == "donut"
        assert "data_field" in report.config
        assert "colors" in report.config

    def test_task_completion_timeline_report_definition(self):
        """Test TASK_COMPLETION_TIMELINE_REPORT definition."""
        report = TASK_COMPLETION_TIMELINE_REPORT

        assert report.name == "Task Completion Timeline"
        assert report.data_source_type == "tasks"
        assert report.visualization_type == "timeline"
        assert "period" in report.filters
        assert "priority" in report.filters
        assert report.config["chart_type"] == "timeline"
        assert "data_field" in report.config
        assert "time_field" in report.config

    def test_get_tasks_report_definitions(self):
        """Test get_tasks_report_definitions function."""
        definitions = get_tasks_report_definitions()

        assert isinstance(definitions, dict)
        assert len(definitions) == 6

        # Check all expected reports are present
        expected_keys = [
            "tasks_by_status",
            "tasks_trends",
            "custom_states_usage",
            "productivity_metrics",
            "tasks_by_priority",
            "task_completion_timeline",
        ]

        for key in expected_keys:
            assert key in definitions
            assert definitions[key] is not None

    def test_get_report_definition_existing(self):
        """Test get_report_definition with existing report."""
        report = get_report_definition("tasks_by_status")

        assert report is not None
        assert report.name == "Tasks by Status"
        assert report.data_source_type == "tasks"

    def test_get_report_definition_nonexistent(self):
        """Test get_report_definition with non-existent report."""
        report = get_report_definition("nonexistent_report")

        assert report is None

    def test_validate_report_config_pie_chart(self):
        """Test validate_report_config for pie chart."""
        # Valid config
        valid_config = {"data_field": "by_status"}
        assert validate_report_config(TASKS_BY_STATUS_REPORT, valid_config) is True

        # Invalid config - missing data_field
        invalid_config = {"chart_type": "pie"}
        assert validate_report_config(TASKS_BY_STATUS_REPORT, invalid_config) is False

    def test_validate_report_config_line_chart(self):
        """Test validate_report_config for line chart."""
        # Valid config
        valid_config = {
            "data_field": "data_points",
            "x_axis": "period",
            "y_axis": ["created", "completed"],
        }
        assert validate_report_config(TASKS_TRENDS_REPORT, valid_config) is True

        # Invalid config - missing x_axis
        invalid_config = {
            "data_field": "data_points",
            "y_axis": ["created", "completed"],
        }
        assert validate_report_config(TASKS_TRENDS_REPORT, invalid_config) is False

    def test_validate_report_config_bar_chart(self):
        """Test validate_report_config for bar chart."""
        # Valid config
        valid_config = {
            "data_field": "task_count",
            "x_axis": "state_name",
            "y_axis": "task_count",
        }
        assert validate_report_config(CUSTOM_STATES_USAGE_REPORT, valid_config) is True

        # Invalid config - missing y_axis
        invalid_config = {"data_field": "task_count", "x_axis": "state_name"}
        assert (
            validate_report_config(CUSTOM_STATES_USAGE_REPORT, invalid_config) is False
        )

    def test_validate_report_config_kpi(self):
        """Test validate_report_config for KPI."""
        # Valid config
        valid_config = {
            "data_field": "productivity_data",  # Required field
            "kpis": [{"title": "Total", "data_field": "total", "format": "number"}],
        }
        assert validate_report_config(PRODUCTIVITY_METRICS_REPORT, valid_config) is True

        # Invalid config - kpis not a list
        invalid_config = {"data_field": "productivity_data", "kpis": "not_a_list"}
        assert (
            validate_report_config(PRODUCTIVITY_METRICS_REPORT, invalid_config) is False
        )

    def test_validate_report_config_timeline(self):
        """Test validate_report_config for timeline."""
        # Valid config
        valid_config = {"data_field": "completed_tasks", "time_field": "completed_at"}
        assert (
            validate_report_config(TASK_COMPLETION_TIMELINE_REPORT, valid_config)
            is True
        )

        # Invalid config - missing time_field
        invalid_config = {"data_field": "completed_tasks"}
        assert (
            validate_report_config(TASK_COMPLETION_TIMELINE_REPORT, invalid_config)
            is False
        )

    def test_validate_report_config_unknown_type(self):
        """Test validate_report_config with unknown visualization type."""
        # Create a mock report with unknown type
        from app.models.reporting import ReportDefinition

        unknown_report = ReportDefinition(
            name="Unknown", data_source_type="tasks", visualization_type="unknown_type"
        )

        # Should return False for unknown types
        assert validate_report_config(unknown_report, {"data_field": "test"}) is False

    def test_all_reports_have_required_fields(self):
        """Test that all report definitions have required fields."""
        definitions = get_tasks_report_definitions()

        for report_id, report in definitions.items():
            # Check required fields
            assert hasattr(report, "name"), f"Report {report_id} missing name"
            assert hasattr(
                report, "data_source_type"
            ), f"Report {report_id} missing data_source_type"
            assert hasattr(
                report, "visualization_type"
            ), f"Report {report_id} missing visualization_type"

            # Check values are not empty
            assert report.name, f"Report {report_id} has empty name"
            assert (
                report.data_source_type
            ), f"Report {report_id} has empty data_source_type"
            assert (
                report.visualization_type
            ), f"Report {report_id} has empty visualization_type"

            # Check that data_source_type is "tasks"
            assert (
                report.data_source_type == "tasks"
            ), f"Report {report_id} has wrong data_source_type"

    def test_all_reports_have_valid_config(self):
        """Test that all report definitions have valid configuration."""
        definitions = get_tasks_report_definitions()

        for report_id, report in definitions.items():
            assert report.config is not None, f"Report {report_id} missing config"
            assert isinstance(
                report.config, dict
            ), f"Report {report_id} config is not a dict"

            # Validate the config
            is_valid = validate_report_config(report, report.config)
            assert is_valid, f"Report {report_id} has invalid config"

    def test_report_definitions_registry_completeness(self):
        """Test that TASKS_REPORT_DEFINITIONS matches get_tasks_report_definitions."""
        registry_definitions = TASKS_REPORT_DEFINITIONS
        function_definitions = get_tasks_report_definitions()

        assert len(registry_definitions) == len(function_definitions)

        for key in registry_definitions:
            assert key in function_definitions
            assert registry_definitions[key] is function_definitions[key]

    def test_filter_definitions_structure(self):
        """Test that filter definitions have proper structure."""
        definitions = get_tasks_report_definitions()

        for report_id, report in definitions.items():
            if report.filters:
                for filter_name, filter_def in report.filters.items():
                    assert (
                        "type" in filter_def
                    ), f"Report {report_id} filter {filter_name} missing type"
                    assert (
                        "label" in filter_def
                    ), f"Report {report_id} filter {filter_name} missing label"

                    # Check select filters have options
                    if filter_def["type"] in ["select", "multi_select"]:
                        assert (
                            "options" in filter_def
                        ), f"Report {report_id} filter {filter_name} missing options"
                        assert isinstance(
                            filter_def["options"], list
                        ), f"Report {report_id} filter {filter_name} options not a list"
