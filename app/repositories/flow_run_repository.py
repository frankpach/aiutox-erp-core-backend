"""Flow Run repository for data access operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.flow_run import FlowRun, FlowRunStatus


class FlowRunRepository:
    """Repository for flow run data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_flow_run(self, flow_run_data: dict) -> FlowRun:
        """Create a new flow run."""
        flow_run = FlowRun(**flow_run_data)
        self.db.add(flow_run)
        self.db.commit()
        self.db.refresh(flow_run)
        return flow_run

    def get_flow_run_by_id(self, run_id: UUID, tenant_id: UUID) -> FlowRun | None:
        """Get flow run by ID and tenant."""
        return (
            self.db.query(FlowRun)
            .filter(
                FlowRun.id == run_id,
                FlowRun.tenant_id == tenant_id,
            )
            .first()
        )

    def get_flow_run_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> FlowRun | None:
        """Get flow run by entity type and ID."""
        return (
            self.db.query(FlowRun)
            .filter(
                FlowRun.entity_type == entity_type,
                FlowRun.entity_id == entity_id,
                FlowRun.tenant_id == tenant_id,
            )
            .first()
        )

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
        query = self.db.query(FlowRun).filter(FlowRun.tenant_id == tenant_id)

        if flow_id:
            query = query.filter(FlowRun.flow_id == flow_id)
        if status:
            query = query.filter(FlowRun.status == status)
        if entity_type:
            query = query.filter(FlowRun.entity_type == entity_type)

        return (
            query.order_by(FlowRun.created_at.desc()).offset(offset).limit(limit).all()
        )

    def update_flow_run(
        self, run_id: UUID, tenant_id: UUID, update_data: dict
    ) -> FlowRun | None:
        """Update flow run."""
        flow_run = self.get_flow_run_by_id(run_id, tenant_id)
        if flow_run:
            for key, value in update_data.items():
                setattr(flow_run, key, value)
            self.db.commit()
            self.db.refresh(flow_run)
        return flow_run

    def update_flow_run_status(
        self, run_id: UUID, tenant_id: UUID, status: str
    ) -> FlowRun | None:
        """Update flow run status."""
        update_data = {"status": status}

        if status == FlowRunStatus.RUNNING.value:
            update_data["started_at"] = datetime.now(UTC)
        elif status in [
            FlowRunStatus.COMPLETED.value,
            FlowRunStatus.FAILED.value,
            FlowRunStatus.CANCELLED.value,
        ]:
            update_data["completed_at"] = datetime.now(UTC)

        return self.update_flow_run(run_id, tenant_id, update_data)

    def delete_flow_run(self, run_id: UUID, tenant_id: UUID) -> bool:
        """Delete flow run."""
        flow_run = self.get_flow_run_by_id(run_id, tenant_id)
        if flow_run:
            self.db.delete(flow_run)
            self.db.commit()
            return True
        return False

    def get_flow_runs_stats(self, tenant_id: UUID) -> dict:
        """Get flow run statistics."""
        total = self.db.query(FlowRun).filter(FlowRun.tenant_id == tenant_id).count()

        pending = (
            self.db.query(FlowRun)
            .filter(
                FlowRun.tenant_id == tenant_id,
                FlowRun.status == FlowRunStatus.PENDING.value,
            )
            .count()
        )

        running = (
            self.db.query(FlowRun)
            .filter(
                FlowRun.tenant_id == tenant_id,
                FlowRun.status == FlowRunStatus.RUNNING.value,
            )
            .count()
        )

        completed = (
            self.db.query(FlowRun)
            .filter(
                FlowRun.tenant_id == tenant_id,
                FlowRun.status == FlowRunStatus.COMPLETED.value,
            )
            .count()
        )

        failed = (
            self.db.query(FlowRun)
            .filter(
                FlowRun.tenant_id == tenant_id,
                FlowRun.status == FlowRunStatus.FAILED.value,
            )
            .count()
        )

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
        }
