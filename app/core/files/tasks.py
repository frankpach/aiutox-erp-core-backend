"""Async tasks for the Files module."""

import logging
from typing import Any
from uuid import UUID

from app.core.async_tasks import Task, register_task
from app.core.db.deps import get_db
from app.core.files.service import FileService

logger = logging.getLogger(__name__)


@register_task(
    module="files",
    name="cleanup_deleted_files",
    schedule={"type": "interval", "hours": 24},  # Diario
    description="Limpia archivos eliminados después del período de retención",
    enabled=True,
)
class CleanupDeletedFilesTask(Task):
    """Task to clean up deleted files after retention period."""

    async def execute(self, tenant_id: UUID, **kwargs) -> dict[str, Any]:
        """Execute the cleanup task.

        Args:
            tenant_id: Tenant ID
            **kwargs: Additional parameters (retention_days can be passed)

        Returns:
            Dict with cleanup statistics
        """
        # Import here to avoid circular imports

        # Get database session
        db = next(get_db())

        try:
            # Create FileService
            service = FileService(db, tenant_id=tenant_id)

            # Get retention_days from kwargs or use default
            retention_days = kwargs.get("retention_days")

            # Execute cleanup
            result = await service.cleanup_deleted_files(tenant_id, retention_days)

            logger.info(
                f"Cleanup task completed for tenant {tenant_id}: "
                f"{result['files_count']} files deleted, "
                f"{result['storage_freed']} bytes freed"
            )

            return {
                "files_deleted": result["files_count"],
                "storage_freed": result["storage_freed"],
                "errors": result.get("errors", []),
                "tenant_id": str(tenant_id),
            }
        except Exception as e:
            logger.error(
                f"Error executing cleanup task for tenant {tenant_id}: {e}",
                exc_info=True,
            )
            raise
        finally:
            db.close()

