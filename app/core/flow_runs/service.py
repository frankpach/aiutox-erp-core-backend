"""Flow Run service for managing workflow executions."""

from uuid import UUID
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from app.models.flow_run import FlowRun, FlowRunStatus
from app.repositories.flow_run_repository import FlowRunRepository


class FlowRunService:
    """Service for managing flow runs."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = FlowRunRepository(db)

    def create_flow_run(
        self,
        flow_id: UUID | None,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> FlowRun:
        """Create a new flow run."""
        flow_run_data = {
            "flow_id": flow_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "tenant_id": tenant_id,
            "status": FlowRunStatus.PENDING.value,
            "metadata": metadata or {},
        }
        return self.repository.create_flow_run(flow_run_data)

    def get_flow_run_by_id(self, run_id: UUID, tenant_id: UUID) -> FlowRun | None:
        """Get flow run by ID."""
        return self.repository.get_flow_run_by_id(run_id, tenant_id)

    def get_flow_run_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> FlowRun | None:
        """Get flow run by entity."""
        return self.repository.get_flow_run_by_entity(entity_type, entity_id, tenant_id)

    def get_flow_runs(
        self,
        tenant_id: UUID,
        flow_id: UUID | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FlowRun]:
        """Get flow runs with optional filters."""
        return self.repository.get_flow_runs(
            tenant_id=tenant_id,
            flow_id=flow_id,
            status=status,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )

    def start_flow_run(self, run_id: UUID, tenant_id: UUID) -> FlowRun | None:
        """Start a flow run."""
        return self.repository.update_flow_run_status(
            run_id, tenant_id, FlowRunStatus.RUNNING.value
        )

    def complete_flow_run(
        self, run_id: UUID, tenant_id: UUID, metadata: dict[str, Any] | None = None
    ) -> FlowRun | None:
        """Complete a flow run."""
        update_data = {"metadata": metadata}
        flow_run = self.repository.update_flow_run(
            run_id, tenant_id, update_data
        )
        if flow_run:
            return self.repository.update_flow_run_status(
                run_id, tenant_id, FlowRunStatus.COMPLETED.value
            )
        return None

    def fail_flow_run(
        self,
        run_id: UUID,
        tenant_id: UUID,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FlowRun | None:
        """Fail a flow run."""
        update_data = {
            "error_message": error_message,
            "metadata": metadata,
        }
        flow_run = self.repository.update_flow_run(
            run_id, tenant_id, update_data
        )
        if flow_run:
            return self.repository.update_flow_run_status(
                run_id, tenant_id, FlowRunStatus.FAILED.value
            )
        return None

    def cancel_flow_run(self, run_id: UUID, tenant_id: UUID) -> FlowRun | None:
        """Cancel a flow run."""
        return self.repository.update_flow_run_status(
            run_id, tenant_id, FlowRunStatus.CANCELLED.value
        )

    def delete_flow_run(self, run_id: UUID, tenant_id: UUID) -> bool:
        """Delete a flow run."""
        return self.repository.delete_flow_run(run_id, tenant_id)

    def get_flow_runs_stats(self, tenant_id: UUID) -> dict[str, int]:
        """Get flow run statistics."""
        return self.repository.get_flow_runs_stats(tenant_id)
