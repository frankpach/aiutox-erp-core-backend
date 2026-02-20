"""Report definitions for tasks statistics and reporting."""

from typing import Any

from app.models.reporting import ReportDefinition

# Tasks by Status Report
TASKS_BY_STATUS_REPORT = ReportDefinition(
    name="Tasks by Status",
    description="Distribution of tasks across different statuses",
    data_source_type="tasks",
    visualization_type="pie_chart",
    filters={
        "date_range": {"type": "date_range", "label": "Date Range", "default": "30d"}
    },
    config={
        "chart_type": "pie",
        "data_field": "by_status",
        "colors": {
            "todo": "#6B7280",
            "in_progress": "#3B82F6",
            "done": "#10B981",
            "cancelled": "#EF4444",
        },
        "show_labels": True,
        "show_percentages": True,
    },
)

# Tasks Trends Report
TASKS_TRENDS_REPORT = ReportDefinition(
    name="Tasks Trends",
    description="Task creation and completion trends over time",
    data_source_type="tasks",
    visualization_type="line_chart",
    filters={
        "period": {
            "type": "select",
            "label": "Period",
            "options": [
                {"value": "7d", "label": "Last 7 days"},
                {"value": "30d", "label": "Last 30 days"},
                {"value": "90d", "label": "Last 90 days"},
            ],
            "default": "30d",
        }
    },
    config={
        "chart_type": "line",
        "data_field": "data_points",
        "x_axis": "period",
        "y_axis": ["created", "completed"],
        "colors": {"created": "#3B82F6", "completed": "#10B981"},
        "show_points": True,
        "show_grid": True,
    },
)

# Custom States Usage Report
CUSTOM_STATES_USAGE_REPORT = ReportDefinition(
    name="Custom States Usage",
    description="Usage metrics for custom task states",
    data_source_type="tasks",
    visualization_type="bar_chart",
    filters={
        "state_type": {
            "type": "select",
            "label": "State Type",
            "options": [
                {"value": "open", "label": "Open"},
                {"value": "in_progress", "label": "In Progress"},
                {"value": "closed", "label": "Closed"},
            ],
        }
    },
    config={
        "chart_type": "bar",
        "data_field": "task_count",
        "x_axis": "state_name",
        "y_axis": "task_count",
        "color_field": "state_color",
        "show_values": True,
        "sort_by": "task_count",
        "sort_order": "desc",
    },
)

# Productivity Metrics Report
PRODUCTIVITY_METRICS_REPORT = ReportDefinition(
    name="Productivity Metrics",
    description="Key productivity indicators for tasks",
    data_source_type="tasks",
    visualization_type="kpi",
    filters={
        "date_range": {"type": "date_range", "label": "Date Range", "default": "30d"}
    },
    config={
        "kpis": [
            {
                "title": "Total Tasks",
                "data_field": "total_tasks",
                "format": "number",
                "icon": "tasks",
            },
            {
                "title": "Completion Rate",
                "data_field": "completion_rate",
                "format": "percentage",
                "icon": "check_circle",
            },
            {
                "title": "Overdue Tasks",
                "data_field": "overdue_tasks",
                "format": "number",
                "icon": "warning",
                "color_threshold": {"warning": 5, "danger": 10},
            },
            {
                "title": "Avg Time in Custom States",
                "data_field": "avg_time_in_custom_states",
                "format": "hours",
                "icon": "clock",
            },
        ],
        "layout": "grid_2x2",
    },
)

# Tasks by Priority Report
TASKS_BY_PRIORITY_REPORT = ReportDefinition(
    name="Tasks by Priority",
    description="Distribution of tasks by priority level",
    data_source_type="tasks",
    visualization_type="donut_chart",
    filters={
        "status_filter": {
            "type": "select",
            "label": "Status Filter",
            "options": [
                {"value": "all", "label": "All Tasks"},
                {"value": "active", "label": "Active Only"},
                {"value": "completed", "label": "Completed Only"},
            ],
            "default": "active",
        }
    },
    config={
        "chart_type": "donut",
        "data_field": "by_priority",
        "colors": {
            "urgent": "#DC2626",
            "high": "#F59E0B",
            "medium": "#3B82F6",
            "low": "#6B7280",
        },
        "show_labels": True,
        "center_text": "Tasks",
    },
)

# Task Completion Timeline Report
TASK_COMPLETION_TIMELINE_REPORT = ReportDefinition(
    name="Task Completion Timeline",
    description="Timeline of task completions with average completion time",
    data_source_type="tasks",
    visualization_type="timeline",
    filters={
        "period": {
            "type": "select",
            "label": "Period",
            "options": [
                {"value": "7d", "label": "Last 7 days"},
                {"value": "30d", "label": "Last 30 days"},
            ],
            "default": "30d",
        },
        "priority": {
            "type": "multi_select",
            "label": "Priority",
            "options": [
                {"value": "urgent", "label": "Urgent"},
                {"value": "high", "label": "High"},
                {"value": "medium", "label": "Medium"},
                {"value": "low", "label": "Low"},
            ],
        },
    },
    config={
        "chart_type": "timeline",
        "data_field": "completed_tasks",
        "time_field": "completed_at",
        "group_by": "priority",
        "show_avg_time": True,
        "time_format": "relative",
    },
)

# Registry of all task report definitions
TASKS_REPORT_DEFINITIONS: dict[str, ReportDefinition] = {
    "tasks_by_status": TASKS_BY_STATUS_REPORT,
    "tasks_trends": TASKS_TRENDS_REPORT,
    "custom_states_usage": CUSTOM_STATES_USAGE_REPORT,
    "productivity_metrics": PRODUCTIVITY_METRICS_REPORT,
    "tasks_by_priority": TASKS_BY_PRIORITY_REPORT,
    "task_completion_timeline": TASK_COMPLETION_TIMELINE_REPORT,
}


def get_tasks_report_definitions() -> dict[str, ReportDefinition]:
    """Get all task report definitions.

    Returns:
        Dictionary mapping report IDs to ReportDefinition objects
    """
    return TASKS_REPORT_DEFINITIONS


def get_report_definition(report_id: str) -> ReportDefinition | None:
    """Get a specific report definition by ID.

    Args:
        report_id: Report definition ID

    Returns:
        ReportDefinition if found, None otherwise
    """
    return TASKS_REPORT_DEFINITIONS.get(report_id)


def validate_report_config(
    report_def: ReportDefinition, config: dict[str, Any]
) -> bool:
    """Validate report configuration against definition.

    Args:
        report_def: Report definition
        config: Configuration to validate

    Returns:
        True if valid, False otherwise
    """
    # Validate visualization-specific config
    viz_type = report_def.visualization_type

    if viz_type in ["pie_chart", "donut_chart"]:
        return "data_field" in config

    elif viz_type == "line_chart":
        return all(field in config for field in ["data_field", "x_axis", "y_axis"])

    elif viz_type == "bar_chart":
        return all(field in config for field in ["data_field", "x_axis", "y_axis"])

    elif viz_type == "kpi":
        return "kpis" in config and isinstance(config["kpis"], list)

    elif viz_type == "timeline":
        return all(field in config for field in ["data_field", "time_field"])

    else:
        # Unknown visualization type
        return False
