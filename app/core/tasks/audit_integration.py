"""Audit integration service for Tasks module."""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskAuditService:
    """Service for integrating task operations with audit system."""

    def __init__(self, db):
        """Initialize audit service integration."""
        self.db = db
        # Connect to existing audit service
        try:
            from app.services.audit_service import AuditService
            self.audit_service = AuditService(db)
            self.is_connected = True
            logger.info("TaskAuditService connected to AuditService")
        except ImportError:
            logger.warning("AuditService not found, using fallback logging")
            self.audit_service = None
            self.is_connected = False
        except Exception as e:
            logger.error(f"Failed to connect to AuditService: {e}")
            self.audit_service = None
            self.is_connected = False

    async def log_task_created(
        self,
        task_id: UUID,
        title: str,
        priority: str,
        created_by_id: UUID,
        tenant_id: UUID,
        additional_data: dict | None = None
    ) -> None:
        """Log task creation in audit system."""
        try:
            audit_data = {
                "action": "task_created",
                "resource_type": "task",
                "resource_id": str(task_id),
                "user_id": str(created_by_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "title": title,
                    "priority": priority,
                    **(additional_data or {})
                }
            }

            if self.is_connected and self.audit_service:
                # Use real audit service
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Task creation logged to audit system: {task_id}")
            else:
                # Fallback: Log locally
                logger.info(f"Task created audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log task creation audit: {e}")

    async def log_task_updated(
        self,
        task_id: UUID,
        changes: dict,
        updated_by_id: UUID,
        tenant_id: UUID,
        old_values: dict | None = None
    ) -> None:
        """Log task update in audit system."""
        try:
            audit_data = {
                "action": "task_updated",
                "resource_type": "task",
                "resource_id": str(task_id),
                "user_id": str(updated_by_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "changes": changes,
                    "old_values": old_values or {}
                }
            }

            if self.is_connected and self.audit_service:
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Task update logged to audit system: {task_id}")
            else:
                logger.info(f"Task updated audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log task update audit: {e}")

    async def log_task_deleted(
        self,
        task_id: UUID,
        title: str,
        deleted_by_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Log task deletion in audit system."""
        try:
            audit_data = {
                "action": "task_deleted",
                "resource_type": "task",
                "resource_id": str(task_id),
                "user_id": str(deleted_by_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "title": title
                }
            }

            if self.is_connected and self.audit_service:
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Task deletion logged to audit system: {task_id}")
            else:
                logger.info(f"Task deleted audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log task deletion audit: {e}")

    async def log_task_status_changed(
        self,
        task_id: UUID,
        title: str,
        old_status: str,
        new_status: str,
        changed_by_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Log task status change in audit system."""
        try:
            audit_data = {
                "action": "task_status_changed",
                "resource_type": "task",
                "resource_id": str(task_id),
                "user_id": str(changed_by_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "title": title,
                    "old_status": old_status,
                    "new_status": new_status
                }
            }

            if self.is_connected and self.audit_service:
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Task status change logged to audit system: {task_id}")
            else:
                logger.info(f"Task status changed audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log task status change audit: {e}")

    async def log_task_assigned(
        self,
        task_id: UUID,
        title: str,
        old_assigned_to_id: UUID | None,
        new_assigned_to_id: UUID,
        assigned_by_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Log task assignment in audit system."""
        try:
            audit_data = {
                "action": "task_assigned",
                "resource_type": "task",
                "resource_id": str(task_id),
                "user_id": str(assigned_by_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "title": title,
                    "old_assigned_to_id": str(old_assigned_to_id) if old_assigned_to_id else None,
                    "new_assigned_to_id": str(new_assigned_to_id)
                }
            }

            if self.is_connected and self.audit_service:
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Task assignment logged to audit system: {task_id}")
            else:
                logger.info(f"Task assigned audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log task assignment audit: {e}")

    async def log_bulk_operation(
        self,
        operation_type: str,
        task_ids: list[UUID],
        user_id: UUID,
        tenant_id: UUID,
        results: dict
    ) -> None:
        """Log bulk operation in audit system."""
        try:
            audit_data = {
                "action": f"bulk_{operation_type}",
                "resource_type": "task",
                "resource_ids": [str(tid) for tid in task_ids],
                "user_id": str(user_id),
                "tenant_id": str(tenant_id),
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "operation_type": operation_type,
                    "task_count": len(task_ids),
                    "successful": results.get("successful", 0),
                    "failed": results.get("failed", 0),
                    "success_rate": results.get("success_rate", 0)
                }
            }

            if self.is_connected and self.audit_service:
                await self.audit_service.create_audit_log(audit_data)
                logger.info(f"Bulk operation logged to audit system: {operation_type}")
            else:
                logger.info(f"Bulk operation audit (fallback): {audit_data}")

        except Exception as e:
            logger.error(f"Failed to log bulk operation audit: {e}")


# Global audit service instance factory
def get_task_audit_service(db) -> TaskAuditService:
    """Get TaskAuditService instance."""
    return TaskAuditService(db)
