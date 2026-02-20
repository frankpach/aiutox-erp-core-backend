"""Visualization types for reporting."""

from typing import Any


class TableVisualization:
    """Table visualization for reports."""

    def render(
        self, data: list[dict[str, Any]], config: dict[str, Any]
    ) -> dict[str, Any]:
        """Render data as a table.

        Args:
            data: List of data rows
            config: Visualization configuration

        Returns:
            Dictionary with table visualization data
        """
        return {
            "type": "table",
            "data": data,
            "config": config,
        }


class ChartVisualization:
    """Chart visualization for reports."""

    def render(
        self, data: list[dict[str, Any]], config: dict[str, Any]
    ) -> dict[str, Any]:
        """Render data as a chart.

        Args:
            data: List of data rows
            config: Visualization configuration (chart_type, x_axis, y_axis, etc.)

        Returns:
            Dictionary with chart visualization data
        """
        chart_type = config.get("chart_type", "bar")
        return {
            "type": "chart",
            "chart_type": chart_type,
            "data": data,
            "config": config,
        }


class KPIVisualization:
    """KPI visualization for reports."""

    def render(
        self, data: list[dict[str, Any]], config: dict[str, Any]
    ) -> dict[str, Any]:
        """Render data as KPI metrics.

        Args:
            data: List of data rows (typically single row for KPI)
            config: Visualization configuration (metric_field, format, etc.)

        Returns:
            Dictionary with KPI visualization data
        """
        metric_field = config.get("metric_field", "value")
        value = data[0].get(metric_field, 0) if data else 0

        return {
            "type": "kpi",
            "value": value,
            "config": config,
        }
