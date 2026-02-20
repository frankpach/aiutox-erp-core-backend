"""Reporting engine for executing reports."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.reporting.data_source import BaseDataSource
from app.core.reporting.visualizations import (
    ChartVisualization,
    KPIVisualization,
    TableVisualization,
)
from app.models.reporting import ReportDefinition

logger = logging.getLogger(__name__)


class ReportingEngine:
    """Engine for executing reports."""

    def __init__(self, db: Session):
        """Initialize reporting engine.

        Args:
            db: Database session
        """
        self.db = db
        self._data_sources: dict[str, type[BaseDataSource]] = {}

    def register_data_source(
        self, source_type: str, data_source_class: type[BaseDataSource]
    ) -> None:
        """Register a data source class.

        Args:
            source_type: Data source type identifier (e.g., 'products')
            data_source_class: Data source class that inherits from BaseDataSource
        """
        self._data_sources[source_type] = data_source_class
        logger.info(f"Registered data source: {source_type}")

    async def execute(
        self,
        report_def: ReportDefinition,
        filters: dict[str, Any] | None = None,
        pagination: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Execute a report.

        Args:
            report_def: Report definition
            filters: Additional filters to apply
            pagination: Pagination configuration

        Returns:
            Dictionary with report data and visualization

        Raises:
            ValueError: If data source type is not registered
        """
        # Get data source class
        data_source_class = self._data_sources.get(report_def.data_source_type)
        if not data_source_class:
            raise ValueError(
                f"Data source type '{report_def.data_source_type}' is not registered"
            )

        # Create data source instance
        data_source = data_source_class(self.db, report_def.tenant_id)

        # Merge filters
        merged_filters = report_def.filters or {}
        if filters:
            merged_filters.update(filters)

        # Get data
        data_result = await data_source.get_data(merged_filters, pagination)

        # Apply visualization
        visualization = self._get_visualization(report_def.visualization_type)
        visualization_result = visualization.render(
            data_result["data"], report_def.config or {}
        )

        return {
            "data": data_result["data"],
            "total": data_result["total"],
            "visualization": visualization_result,
            "columns": data_source.get_columns(),
        }

    def _get_visualization(self, visualization_type: str):
        """Get visualization instance.

        Args:
            visualization_type: Type of visualization ('table', 'chart', 'kpi')

        Returns:
            Visualization instance

        Raises:
            ValueError: If visualization type is not supported
        """
        if visualization_type == "table":
            return TableVisualization()
        elif visualization_type == "chart":
            return ChartVisualization()
        elif visualization_type == "kpi":
            return KPIVisualization()
        else:
            raise ValueError(f"Unsupported visualization type: {visualization_type}")
