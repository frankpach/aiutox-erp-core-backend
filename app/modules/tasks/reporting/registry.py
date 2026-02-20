"""Registry for integrating tasks widgets with reporting system."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.reporting.engine import ReportingEngine
from app.modules.tasks.reporting.data_source import TasksDataSource
from app.modules.tasks.reporting.definitions import (
    CUSTOM_STATES_USAGE_REPORT,
    PRODUCTIVITY_METRICS_REPORT,
    TASK_COMPLETION_TIMELINE_REPORT,
    TASKS_BY_PRIORITY_REPORT,
    TASKS_BY_STATUS_REPORT,
    TASKS_TRENDS_REPORT,
)

logger = logging.getLogger(__name__)


def register_tasks_data_sources(engine: ReportingEngine) -> None:
    """Register tasks data sources with the reporting engine.

    Args:
        engine: ReportingEngine instance to register data sources with
    """
    # Register the main tasks data source
    engine.register_data_source("tasks", TasksDataSource)
    logger.info("Registered tasks data source with reporting engine")


def get_tasks_report_definitions() -> dict[str, any]:
    """Get all available tasks report definitions.

    Returns:
        Dictionary mapping report IDs to report definitions
    """
    return {
        "tasks_by_status": TASKS_BY_STATUS_REPORT,
        "tasks_trends": TASKS_TRENDS_REPORT,
        "custom_states_usage": CUSTOM_STATES_USAGE_REPORT,
        "productivity_metrics": PRODUCTIVITY_METRICS_REPORT,
        "tasks_by_priority": TASKS_BY_PRIORITY_REPORT,
        "task_completion_timeline": TASK_COMPLETION_TIMELINE_REPORT,
    }


def create_default_reports(
    db: Session, tenant_id: UUID, created_by: UUID
) -> list[UUID]:
    """Create default tasks reports for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant ID to create reports for
        created_by: User ID creating the reports

    Returns:
        List of created report IDs
    """
    from app.core.reporting.service import ReportingService

    service = ReportingService(db)
    created_report_ids = []

    # Register data sources first
    engine = ReportingEngine(db)
    register_tasks_data_sources(engine)

    # Create default reports
    report_configs = [
        {
            "name": "Tasks by Status",
            "description": "Distribution of tasks across different statuses",
            "data_source_type": "tasks",
            "visualization_type": "pie_chart",
            "report_definition": TASKS_BY_STATUS_REPORT,
        },
        {
            "name": "Tasks Trends",
            "description": "Task creation and completion trends over time",
            "data_source_type": "tasks",
            "visualization_type": "line_chart",
            "report_definition": TASKS_TRENDS_REPORT,
        },
        {
            "name": "Tasks by Priority",
            "description": "Distribution of tasks by priority level",
            "data_source_type": "tasks",
            "visualization_type": "donut_chart",
            "report_definition": TASKS_BY_PRIORITY_REPORT,
        },
        {
            "name": "Custom States Usage",
            "description": "Usage metrics for custom task states",
            "data_source_type": "tasks",
            "visualization_type": "bar_chart",
            "report_definition": CUSTOM_STATES_USAGE_REPORT,
        },
        {
            "name": "Productivity Metrics",
            "description": "Key productivity indicators for tasks",
            "data_source_type": "tasks",
            "visualization_type": "kpi",
            "report_definition": PRODUCTIVITY_METRICS_REPORT,
        },
        {
            "name": "Task Completion Timeline",
            "description": "Timeline of task completions",
            "data_source_type": "tasks",
            "visualization_type": "timeline",
            "report_definition": TASK_COMPLETION_TIMELINE_REPORT,
        },
    ]

    for config in report_configs:
        try:
            report = service.create_report(
                tenant_id=tenant_id,
                name=config["name"],
                data_source_type=config["data_source_type"],
                visualization_type=config["visualization_type"],
                created_by=created_by,
                description=config["description"],
                filters=config["report_definition"].filters,
                config=config["report_definition"].config,
            )
            created_report_ids.append(report.id)
            logger.info(
                f"Created default report '{config['name']}' for tenant {tenant_id}"
            )
        except Exception as e:
            logger.error(f"Failed to create report '{config['name']}': {e}")
            # Continue with other reports

    return created_report_ids


def get_available_widgets(tenant_id: UUID) -> list[dict[str, any]]:
    """Get available widgets for tasks dashboard.

    Args:
        tenant_id: Tenant ID (for future tenant-specific customizations)

    Returns:
        List of available widget configurations
    """
    report_definitions = get_tasks_report_definitions()

    widgets = []
    for widget_id, report_def in report_definitions.items():
        widget_config = {
            "widget_id": widget_id,
            "name": report_def.name,
            "description": report_def.description,
            "data_source_type": report_def.data_source_type,
            "visualization_type": report_def.visualization_type,
            "default_filters": report_def.filters or {},
            "default_config": report_def.config or {},
            "category": "tasks",
        }
        widgets.append(widget_config)

    return widgets


def validate_widget_config(widget_id: str, config: dict[str, any]) -> bool:
    """Validate widget configuration.

    Args:
        widget_id: Widget identifier
        config: Configuration to validate

    Returns:
        True if valid, False otherwise
    """
    report_definitions = get_tasks_report_definitions()
    report_def = report_definitions.get(widget_id)

    if not report_def:
        return False

    # Basic validation - check required fields based on visualization type
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

    return False
