"""Extended audit service for comprehensive task auditing."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskAuditServiceExtended:
    """Servicio de auditoría completa de tareas."""

    def __init__(self, db: Session):
        """Initialize extended audit service."""
        self.db = db

    def log_change(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        old_values: dict,
        new_values: dict,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """Registra cambio completo en auditoría."""
        from app.models.audit_log import AuditLog

        audit_log = AuditLog(
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )

        self.db.add(audit_log)
        self.db.commit()

        logger.info(f"Audit log created for task {task_id}: {action}")

    def get_task_audit_trail(
        self,
        task_id: UUID,
        tenant_id: UUID,
        limit: int = 100
    ) -> list:
        """Obtiene el historial de auditoría de una tarea."""
        from app.models.audit_log import AuditLog

        logs = self.db.query(AuditLog).filter(
            AuditLog.entity_type == "task",
            AuditLog.entity_id == task_id,
            AuditLog.tenant_id == tenant_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()

        return logs

    def export_audit_trail(
        self,
        task_id: UUID,
        tenant_id: UUID,
        format: str = "json"
    ) -> dict | str:
        """Exporta el historial de auditoría."""
        logs = self.get_task_audit_trail(task_id, tenant_id, limit=1000)

        if format == "json":
            return {
                "task_id": str(task_id),
                "tenant_id": str(tenant_id),
                "exported_at": datetime.utcnow().isoformat(),
                "logs": [
                    {
                        "id": str(log.id),
                        "action": log.action,
                        "user_id": str(log.user_id),
                        "old_values": log.old_values,
                        "new_values": log.new_values,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ]
            }
        elif format == "csv":
            # Implementar export CSV
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Action", "User ID", "Old Values", "New Values", "IP", "Created At"])

            for log in logs:
                writer.writerow([
                    str(log.id),
                    log.action,
                    str(log.user_id),
                    str(log.old_values),
                    str(log.new_values),
                    log.ip_address or "",
                    log.created_at.isoformat(),
                ])

            return output.getvalue()

        return {}


def get_task_audit_service_extended(db: Session) -> TaskAuditServiceExtended:
    """Get extended task audit service instance."""
    return TaskAuditServiceExtended(db)
