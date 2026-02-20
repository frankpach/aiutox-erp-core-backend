"""Base data source for reporting infrastructure."""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class BaseDataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, db: Session, tenant_id: Any):
        """Initialize data source.

        Args:
            db: Database session
            tenant_id: Tenant ID for multi-tenancy
        """
        self.db = db
        self.tenant_id = tenant_id

    @abstractmethod
    async def get_data(
        self,
        filters: dict[str, Any] | None = None,
        pagination: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Get data for the report.

        Args:
            filters: Filter configuration
            pagination: Pagination configuration (skip, limit)

        Returns:
            Dictionary with 'data' (list of rows) and 'total' (total count)
        """
        pass

    @abstractmethod
    def get_columns(self) -> list[dict[str, Any]]:
        """Get available columns for this data source.

        Returns:
            List of column definitions with 'name', 'type', 'label', etc.
        """
        pass

    @abstractmethod
    def get_filters(self) -> list[dict[str, Any]]:
        """Get available filters for this data source.

        Returns:
            List of filter definitions with 'name', 'type', 'options', etc.
        """
        pass
