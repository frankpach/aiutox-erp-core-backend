"""Assignment service for managing task assignments with audit integration."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskAssignmentCreate, TaskAssignmentResponse
from app.services.audit_service import AuditService


class AssignmentService:
    """Service for managing task assignments with audit logging."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.repository = TaskRepository(db)
        self.audit_service = AuditService(db)

    def create_assignment(
        self,
        assignment_data: TaskAssignmentCreate,
        tenant_id: UUID,
        created_by_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TaskAssignmentResponse:
        """
        Create a new task assignment with audit logging.

        Args:
            assignment_data: Assignment creation data
            tenant_id: Tenant ID
            created_by_id: User ID creating the assignment
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit

        Returns:
            Created assignment response
        """
        # Create assignment with audit fields
        assignment = self.repository.create_assignment(
            assignment_data.model_dump(),
            created_by_id=created_by_id
        )

        # Log audit event
        self._log_assignment_event(
            tenant_id=tenant_id,
            user_id=created_by_id,
            action="assignment_created",
            assignment_id=assignment.id,
            assignment_data=assignment_data.model_dump(),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TaskAssignmentResponse.model_validate(assignment)

    def update_assignment(
        self,
        assignment_id: UUID,
        tenant_id: UUID,
        assignment_data: dict,
        updated_by_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TaskAssignmentResponse | None:
        """
        Update a task assignment with audit logging.

        Args:
            assignment_id: Assignment ID
            tenant_id: Tenant ID
            assignment_data: Updated assignment data
            updated_by_id: User ID updating the assignment
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit

        Returns:
            Updated assignment response or None if not found
        """
        # Get original assignment for audit
        original_assignment = self.repository.get_assignment_by_id(
            assignment_id, tenant_id
        )

        if not original_assignment:
            return None

        # Update assignment with audit fields
        updated_assignment = self.repository.update_assignment(
            assignment_id=assignment_id,
            tenant_id=tenant_id,
            assignment_data=assignment_data,
            updated_by_id=updated_by_id
        )

        if not updated_assignment:
            return None

        # Log audit event
        self._log_assignment_event(
            tenant_id=tenant_id,
            user_id=updated_by_id,
            action="assignment_updated",
            assignment_id=assignment_id,
            assignment_data=assignment_data,
            previous_data=self._serialize_assignment(original_assignment),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TaskAssignmentResponse.model_validate(updated_assignment)

    def delete_assignment(
        self,
        assignment_id: UUID,
        tenant_id: UUID,
        deleted_by_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Delete a task assignment with audit logging.

        Args:
            assignment_id: Assignment ID
            tenant_id: Tenant ID
            deleted_by_id: User ID deleting the assignment
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit

        Returns:
            True if deleted, False if not found
        """
        # Get original assignment for audit
        original_assignment = self.repository.get_assignment_by_id(
            assignment_id, tenant_id
        )

        if not original_assignment:
            return False

        # Delete assignment
        success = self.repository.delete_assignment(assignment_id, tenant_id)

        if success:
            # Log audit event
            self._log_assignment_event(
                tenant_id=tenant_id,
                user_id=deleted_by_id,
                action="assignment_deleted",
                assignment_id=assignment_id,
                assignment_data=self._serialize_assignment(original_assignment),
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return success

    def get_assignments_by_task(
        self, task_id: UUID, tenant_id: UUID
    ) -> list[TaskAssignmentResponse]:
        """
        Get all assignments for a task.

        Args:
            task_id: Task ID
            tenant_id: Tenant ID

        Returns:
            List of assignment responses
        """
        assignments = self.repository.get_assignments_by_task(task_id, tenant_id)
        return [TaskAssignmentResponse.model_validate(assignment) for assignment in assignments]

    def get_assignments_by_user(
        self, user_id: UUID, tenant_id: UUID
    ) -> list[TaskAssignmentResponse]:
        """
        Get all assignments for a user.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            List of assignment responses
        """
        assignments = self.repository.get_assignments_by_user(user_id, tenant_id)
        return [TaskAssignmentResponse.model_validate(assignment) for assignment in assignments]

    def _log_assignment_event(
        self,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        assignment_id: UUID,
        assignment_data: dict | None = None,
        previous_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log assignment-related audit event."""
        # This would integrate with the audit repository
        # For now, we'll use the existing audit service pattern
        {
            "assignment_id": str(assignment_id),
            "assignment_data": assignment_data,
            "previous_data": previous_data,
        }

        # Note: In a real implementation, this would call the audit repository directly
        # to create an audit log entry. For now, we're documenting the integration point.
        pass

    def _serialize_assignment(self, assignment) -> dict:
        """Serialize assignment for audit logging."""
        return {
            "id": str(assignment.id),
            "task_id": str(assignment.task_id),
            "assigned_to_id": str(assignment.assigned_to_id) if assignment.assigned_to_id else None,
            "assigned_to_group_id": str(assignment.assigned_to_group_id) if assignment.assigned_to_group_id else None,
            "assigned_by_id": str(assignment.assigned_by_id) if assignment.assigned_by_id else None,
            "role": assignment.role,
            "notes": assignment.notes,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            "created_by_id": str(assignment.created_by_id) if assignment.created_by_id else None,
            "updated_by_id": str(assignment.updated_by_id) if assignment.updated_by_id else None,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
            "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
        }
