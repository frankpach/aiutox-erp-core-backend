"""Approval service for approval workflow management."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.event_helpers import safe_publish_event
from app.core.pubsub.models import EventMetadata
from app.core.tasks.service import TaskService
from app.models.approval import (
    ApprovalAction,
    ApprovalDelegation,
    ApprovalFlow,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStep,
)
from app.repositories.approval_repository import ApprovalRepository

if TYPE_CHECKING:
    from app.core.flow_runs.service import FlowRunService

logger = logging.getLogger(__name__)


class FlowEngine:
    """Engine for executing approval flows."""

    def __init__(self, db: Session):
        """Initialize flow engine."""
        self.db = db
        self.repository = ApprovalRepository(db)

    def get_next_step(
        self, request: ApprovalRequest, flow: ApprovalFlow
    ) -> ApprovalStep | None:
        """Get the next step in the approval flow, considering skip conditions."""
        steps = self.repository.get_approval_steps_by_flow(flow.id, request.tenant_id)
        if not steps:
            return None

        # Get current step
        current_step_order = request.current_step

        # Find next step that doesn't have skip conditions met
        for step in steps:
            if step.step_order > current_step_order:
                # Check if this step should be skipped
                if self._should_skip_step(step, request, flow):
                    continue
                return step

        return None

    def _should_skip_step(
        self, step: ApprovalStep, request: ApprovalRequest, flow: ApprovalFlow
    ) -> bool:
        """Check if a step should be skipped based on conditions."""
        # Check if conditions exist and is a dictionary (not None or SQLAlchemy MetaData)
        if not flow.conditions or not isinstance(flow.conditions, dict):
            return False

        # Check step-specific conditions from flow.conditions
        step_conditions = flow.conditions.get(f"step_{step.step_order}")
        if not step_conditions:
            return False

        # Evaluate conditions
        # Example conditions:
        # - {"amount": {"operator": "lt", "value": 1000}} - Skip if amount < 1000
        # - {"entity_type": ["product"]} - Skip if entity_type is "product"

        for field, condition in step_conditions.items():
            if isinstance(condition, dict) and "operator" in condition:
                # Numeric comparison
                operator = condition["operator"]
                value = condition["value"]

                # Get the actual value from request metadata or entity
                actual_value = self._get_request_value(request, field)

                if actual_value is None:
                    continue

                if operator == "lt" and actual_value < value:
                    return True
                elif operator == "lte" and actual_value <= value:
                    return True
                elif operator == "gt" and actual_value > value:
                    return True
                elif operator == "gte" and actual_value >= value:
                    return True
                elif operator == "eq" and actual_value == value:
                    return True
                elif operator == "ne" and actual_value != value:
                    return True
            elif isinstance(condition, list):
                # Value in list check
                actual_value = self._get_request_value(request, field)
                if actual_value in condition:
                    return True

        return False

    def _get_request_value(self, request: ApprovalRequest, field: str) -> any:
        """Get a value from the request for condition evaluation."""
        # Check common request fields
        if field == "entity_type":
            return request.entity_type
        elif field == "entity_id":
            return str(request.entity_id)
        elif field == "requested_by":
            return str(request.requested_by)

        # Check request metadata if available and is a dictionary
        if hasattr(request, "request_metadata") and request.request_metadata and isinstance(request.request_metadata, dict):
            return request.request_metadata.get(field)

        return None

    def get_current_step(
        self, request: ApprovalRequest, flow: ApprovalFlow
    ) -> ApprovalStep | None:
        """Get the current step in the approval flow."""
        steps = self.repository.get_approval_steps_by_flow(flow.id, request.tenant_id)
        if not steps:
            return None

        return next(
            (s for s in steps if s.step_order == request.current_step), None
        )

    def can_approve(
        self, request: ApprovalRequest, user_id: UUID, flow: ApprovalFlow
    ) -> bool:
        """Check if a user can approve the current step."""
        current_step = self.get_current_step(request, flow)
        if not current_step:
            return False

        # Check if user is the approver for this step
        if current_step.approver_type == "user":
            return current_step.approver_id == user_id
        elif current_step.approver_type == "role":
            # Check if user has the role
            return self._check_user_has_role(user_id, current_step.approver_role, request.tenant_id)
        elif current_step.approver_type == "dynamic":
            # Evaluate dynamic rule
            return self._evaluate_dynamic_rule(current_step, request, user_id)

        return False

    def _check_user_has_role(self, user_id: UUID, role_name: str, tenant_id: UUID) -> bool:
        """Check if a user has a specific role."""
        from app.models.user_role import UserRole

        user_role = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id, UserRole.role == role_name)
            .first()
        )
        return user_role is not None

    def _evaluate_dynamic_rule(self, step: ApprovalStep, request: ApprovalRequest, user_id: UUID) -> bool:
        """Evaluate dynamic approver rule."""
        if not step.approver_rule:
            return False

        rule = step.approver_rule

        # Example rule types:
        # - "manager_of_requester": User must be manager of the requester
        # - "department_head": User must be department head
        # - "amount_based": User can approve based on request amount

        if rule.get("type") == "manager_of_requester":
            # TODO: Check if user is manager of request.requested_by
            return False
        elif rule.get("type") == "department_head":
            # TODO: Check if user is department head
            return False
        elif rule.get("type") == "amount_based":
            # Check if user's approval limit covers the request amount
            # This would require accessing request metadata
            return False

        return False

    def process_approval(
        self,
        request: ApprovalRequest,
        user_id: UUID,
        action_type: str,
        comment: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApprovalRequest:
        """Process an approval action."""
        flow = self.repository.get_approval_flow_by_id(request.flow_id, request.tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        current_step = self.get_current_step(request, flow)
        if not current_step:
            raise ValueError("Current step not found")

        # Create action with audit fields
        self.repository.create_approval_action(
            {
                "tenant_id": request.tenant_id,
                "request_id": request.id,
                "action_type": action_type,
                "step_order": current_step.step_order,
                "comment": comment,
                "acted_by": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )

        # Update request based on action
        if action_type == "approve":
            # Check if flow is sequential or parallel
            if flow.flow_type == "sequential":
                # Move to next step or complete
                next_step = self.get_next_step(request, flow)
                if next_step:
                    self.repository.update_approval_request(
                        request, {"current_step": next_step.step_order}
                    )
                else:
                    # All steps completed
                    self.repository.update_approval_request(
                        request,
                        {
                            "status": ApprovalStatus.APPROVED,
                            "completed_at": datetime.now(UTC),
                        },
                    )
            elif flow.flow_type == "parallel":
                # Check if all required approvals are met for current step
                if self._check_parallel_approval_complete(request, flow, current_step):
                    # All required approvals completed, move to next step or complete
                    next_step = self.get_next_step(request, flow)
                    if next_step:
                        self.repository.update_approval_request(
                            request, {"current_step": next_step.step_order}
                        )
                    else:
                        # All steps completed
                        self.repository.update_approval_request(
                            request,
                            {
                                "status": ApprovalStatus.APPROVED,
                                "completed_at": datetime.now(UTC),
                            },
                        )
        elif action_type == "reject":
            self.repository.update_approval_request(
                request,
                {
                    "status": ApprovalStatus.REJECTED,
                    "completed_at": datetime.now(UTC),
                },
            )

        # Refresh request
        self.db.refresh(request)
        return request

    def _check_parallel_approval_complete(
        self, request: ApprovalRequest, flow: ApprovalFlow, step: ApprovalStep
    ) -> bool:
        """Check if parallel approval requirements are met for a step."""
        # Get all actions for this step
        step_actions = self.repository.get_approval_actions_by_request(
            request.id, request.tenant_id
        )
        step_actions = [a for a in step_actions if a.step_order == step.step_order]

        # Count unique approvals (exclude rejections)
        approvals = [a for a in step_actions if a.action_type == "approve"]
        unique_approvers = set(a.acted_by for a in approvals if a.acted_by)

        # Check requirements
        if step.require_all:
            # Need all configured approvers
            # For now, assume we need at least one approval
            # TODO: Get list of configured approvers from step configuration
            return len(unique_approvers) >= 1
        elif step.min_approvals:
            # Need minimum number of approvals
            return len(unique_approvers) >= step.min_approvals
        else:
            # Default: need at least one approval
            return len(unique_approvers) >= 1


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(
        self,
        db: Session,
        task_service: TaskService | None = None,
        notification_service: NotificationService | None = None,
        event_publisher: EventPublisher | None = None,
        flow_runs_service: "FlowRunService | None" = None,
    ):
        """Initialize approval service.

        Args:
            db: Database session
            task_service: TaskService instance (for creating tasks)
            notification_service: NotificationService instance
            event_publisher: EventPublisher instance
            flow_runs_service: FlowRunService instance (for tracking executions)
        """
        self.db = db
        self.repository = ApprovalRepository(db)
        self.flow_engine = FlowEngine(db)
        self.task_service = task_service
        self.notification_service = notification_service or NotificationService(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self.flow_runs_service = flow_runs_service

    def create_approval_flow(
        self,
        flow_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ApprovalFlow:
        """Create a new approval flow."""
        flow_data["tenant_id"] = tenant_id
        flow_data["created_by"] = user_id

        # Validate conditions JSON if provided
        if "conditions" in flow_data and flow_data["conditions"]:
            self._validate_conditions_json(flow_data["conditions"])

        return self.repository.create_approval_flow(flow_data)

    def get_approval_flow(self, flow_id: UUID, tenant_id: UUID) -> ApprovalFlow | None:
        """Get approval flow by ID."""
        return self.repository.get_approval_flow_by_id(flow_id, tenant_id)

    def get_approval_flows(
        self,
        tenant_id: UUID,
        module: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ApprovalFlow]:
        """Get approval flows."""
        return self.repository.get_approval_flows(
            tenant_id, module, is_active, skip, limit
        )

    def update_approval_flow(
        self,
        flow_id: UUID,
        flow_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ApprovalFlow:
        """Update an approval flow."""
        flow = self.repository.get_approval_flow_by_id(flow_id, tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        # Check if flow has active requests
        active_requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            flow_id=flow_id,
            status="pending",
            skip=0,
            limit=1,
        )
        if active_requests:
            raise ValueError("Cannot update flow with active requests")

        # Validate conditions JSON if provided
        if "conditions" in flow_data and flow_data["conditions"]:
            self._validate_conditions_json(flow_data["conditions"])

        # Add updated_by for audit
        flow_data["updated_by"] = user_id

        updated_flow = self.repository.update_approval_flow(flow, flow_data)
        return updated_flow

    def delete_approval_flow(
        self,
        flow_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Soft delete an approval flow."""
        flow = self.repository.get_approval_flow_by_id(flow_id, tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        # Check if flow has active requests
        active_requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            flow_id=flow_id,
            status="pending",
            skip=0,
            limit=1,
        )
        if active_requests:
            raise ValueError("Cannot delete flow with active requests")

        # Soft delete
        self.repository.update_approval_flow(
            flow,
            {
                "deleted_at": datetime.now(UTC),
                "is_active": False,
            },
        )

    def add_approval_step(
        self,
        flow_id: UUID,
        tenant_id: UUID,
        step_data: dict,
    ) -> ApprovalStep:
        """Add a step to an approval flow."""
        step_data["flow_id"] = flow_id
        step_data["tenant_id"] = tenant_id
        return self.repository.create_approval_step(step_data)

    def delete_all_flow_steps(
        self,
        flow_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete all steps for a given flow."""
        self.repository.delete_all_approval_steps(flow_id, tenant_id)

    def get_approval_steps_by_flow(
        self,
        flow_id: UUID,
        tenant_id: UUID,
    ) -> list[ApprovalStep]:
        """Get all steps for a flow."""
        return self.repository.get_approval_steps_by_flow(flow_id, tenant_id)

    def update_approval_step(
        self,
        step_id: UUID,
        flow_id: UUID,
        step_data: dict,
        tenant_id: UUID,
    ) -> ApprovalStep:
        """Update an approval step."""
        step = self.repository.get_approval_step_by_id(step_id, tenant_id)
        if not step:
            raise ValueError("Approval step not found")

        if step.flow_id != flow_id:
            raise ValueError("Step does not belong to this flow")

        # Check if flow has active requests
        active_requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            flow_id=flow_id,
            status="pending",
            skip=0,
            limit=1,
        )
        if active_requests:
            raise ValueError("Cannot update step in flow with active requests")

        updated_step = self.repository.update_approval_step(step, step_data)
        return updated_step

    def delete_approval_step(
        self,
        step_id: UUID,
        flow_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete an approval step."""
        step = self.repository.get_approval_step_by_id(step_id, tenant_id)
        if not step:
            raise ValueError("Approval step not found")

        if step.flow_id != flow_id:
            raise ValueError("Step does not belong to this flow")

        # Check if flow has active requests
        active_requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            flow_id=flow_id,
            status="pending",
            skip=0,
            limit=1,
        )
        if active_requests:
            raise ValueError("Cannot delete step from flow with active requests")

        self.repository.delete_approval_step(step)

    def create_approval_request(
        self,
        request_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        request_data["tenant_id"] = tenant_id
        request_data["requested_by"] = user_id
        request_data["status"] = ApprovalStatus.PENDING

        request = self.repository.create_approval_request(request_data)

        # Create flow run if service is available
        if self.flow_runs_service:
            try:
                logger.info(f"Attempting to create flow run for request {request.id} with tenant_id {tenant_id}")
                flow_run = self.flow_runs_service.create_flow_run(
                    flow_id=request.flow_id,
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    tenant_id=tenant_id,
                    run_metadata={
                        "approval_request_id": str(request.id),
                        "title": request.title,
                        "requested_by": str(user_id),
                    },
                )
                logger.info(f"Created flow run {flow_run.id} for approval request {request.id}")
            except Exception as e:
                logger.error(f"Failed to create flow run for approval request {request.id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        # Send notifications to approvers
        self._notify_approvers(request, tenant_id)

        # Create tasks for approvers
        self._create_approval_tasks(request, tenant_id)

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="approval.requested",
            entity_type="approval_request",
            entity_id=request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="approval_service",
                version="1.0",
                additional_data={
                    "flow_id": str(request.flow_id),
                    "entity_type": request.entity_type,
                    "entity_id": str(request.entity_id),
                },
            ),
        )

        return request

    def _create_approval_tasks(self, request: ApprovalRequest, tenant_id: UUID) -> None:
        """Create tasks for approvers for the current step."""
        if not self.task_service:
            return

        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
        if not flow:
            return

        steps = self.repository.get_approval_steps_by_flow(flow.id, tenant_id)
        current_step = next((s for s in steps if s.step_order == request.current_step), None)

        if not current_step:
            return

        # Get approvers based on step configuration
        approvers = self._get_step_approvers(current_step, request, tenant_id)

        # Create task for each approver
        for approver_id in approvers:
            try:
                self.task_service.create_task(
                    tenant_id=tenant_id,
                    title=f"Aprobar solicitud: {request.title}",
                    description=f"Revisar y aprobar/rechazar la solicitud de {request.entity_type}.",
                    task_type="approval_review",
                    assigned_to=approver_id,
                    due_date=None,
                    priority="medium",
                    metadata={
                        "request_id": str(request.id),
                        "flow_id": str(flow.id),
                        "step_order": current_step.step_order,
                        "entity_type": request.entity_type,
                        "entity_id": str(request.entity_id),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to create task for approver {approver_id}: {e}")

    def _notify_approvers(self, request: ApprovalRequest, tenant_id: UUID) -> None:
        """Send notifications to approvers for the current step."""
        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
        if not flow:
            return

        steps = self.repository.get_approval_steps_by_flow(flow.id, tenant_id)
        current_step = next((s for s in steps if s.step_order == request.current_step), None)

        if not current_step:
            return

        # Get approvers based on step configuration
        approvers = self._get_step_approvers(current_step, request, tenant_id)

        # Send notification to each approver
        for approver_id in approvers:
            try:
                self.notification_service.create_notification(
                    tenant_id=tenant_id,
                    user_id=approver_id,
                    title=f"Nueva solicitud de aprobación: {request.title}",
                    message=f"Tienes una solicitud de aprobación pendiente para {request.entity_type}.",
                    notification_type="approval_request",
                    entity_type="approval_request",
                    entity_id=request.id,
                    metadata={
                        "request_id": str(request.id),
                        "flow_id": str(flow.id),
                        "step_order": current_step.step_order,
                        "entity_type": request.entity_type,
                        "entity_id": str(request.entity_id),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to send notification to approver {approver_id}: {e}")

    def _get_step_approvers(self, step: ApprovalStep, request: ApprovalRequest, tenant_id: UUID) -> list[UUID]:
        """Get list of approver IDs for a step."""
        approvers = []

        if step.approver_type == "user":
            if step.approver_id:
                approvers.append(step.approver_id)
        elif step.approver_type == "role":
            # TODO: Get users with this role
            pass
        elif step.approver_type == "dynamic":
            # TODO: Evaluate dynamic rule to get approvers
            pass

        return approvers

    def get_approval_request(
        self, request_id: UUID, tenant_id: UUID
    ) -> ApprovalRequest | None:
        """Get approval request by ID."""
        return self.repository.get_approval_request_by_id(request_id, tenant_id)

    def get_approval_requests(
        self,
        tenant_id: UUID,
        flow_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        status: str | None = None,
        requested_by: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ApprovalRequest]:
        """Get approval requests."""
        return self.repository.get_approval_requests(
            tenant_id,
            flow_id,
            entity_type,
            entity_id,
            status,
            requested_by,
            skip,
            limit,
        )

    def approve_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        comment: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApprovalRequest:
        """Approve an approval request."""
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        updated_request = self.flow_engine.process_approval(
            request, user_id, "approve", comment, ip_address, user_agent
        )

        # Update flow run if service is available
        if self.flow_runs_service:
            try:
                flow_run = self.flow_runs_service.get_flow_run_by_entity(
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    tenant_id=tenant_id,
                )
                if flow_run:
                    if updated_request.status == ApprovalStatus.APPROVED:
                        self.flow_runs_service.complete_flow_run(
                            run_id=flow_run.id,
                            tenant_id=tenant_id,
                            run_metadata={
                                "approval_request_id": str(request_id),
                                "approved_by": str(user_id),
                                "comment": comment,
                            },
                        )
                        logger.info(f"Completed flow run {flow_run.id} for approved request {request_id}")
                    else:
                        self.flow_runs_service.start_flow_run(flow_run.id, tenant_id)
                        logger.info(f"Started flow run {flow_run.id} for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to update flow run for approval request {request_id}: {e}")

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="approval.approved",
            entity_type="approval_request",
            entity_id=updated_request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="approval_service",
                version="1.0",
                additional_data={"request_title": updated_request.title},
            ),
        )

        return updated_request

    def reject_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        comment: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApprovalRequest:
        """Reject an approval request."""
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        updated_request = self.flow_engine.process_approval(
            request, user_id, "reject", comment, ip_address, user_agent
        )

        # Update flow run if service is available
        if self.flow_runs_service:
            try:
                flow_run = self.flow_runs_service.get_flow_run_by_entity(
                    entity_type=request.entity_type,
                    entity_id=request.entity_id,
                    tenant_id=tenant_id,
                )
                if flow_run:
                    if updated_request.status == ApprovalStatus.REJECTED:
                        self.flow_runs_service.fail_flow_run(
                            run_id=flow_run.id,
                            tenant_id=tenant_id,
                            error_message="Approval request rejected",
                            run_metadata={
                                "approval_request_id": str(request_id),
                                "rejected_by": str(user_id),
                                "comment": comment,
                            },
                        )
                        logger.info(f"Failed flow run {flow_run.id} for rejected request {request_id}")
                    else:
                        self.flow_runs_service.start_flow_run(flow_run.id, tenant_id)
                        logger.info(f"Started flow run {flow_run.id} for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to update flow run for approval request {request_id}: {e}")

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="approval.rejected",
            entity_type="approval_request",
            entity_id=updated_request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="approval_service",
                version="1.0",
                additional_data={"request_title": updated_request.title},
            ),
        )

        return updated_request

    def delegate_approval(
        self,
        request_id: UUID,
        tenant_id: UUID,
        from_user_id: UUID,
        to_user_id: UUID,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> ApprovalDelegation:
        """Delegate an approval to another user."""
        # Get request and flow
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        # Check if user can approve this request (can only delegate own approvals)
        if not self.flow_engine.can_approve(request, from_user_id, flow):
            raise ValueError("User cannot delegate approval for this request")

        # Check if delegation is to the same user
        if from_user_id == to_user_id:
            raise ValueError("Cannot delegate approval to yourself")

        delegation = self.repository.create_approval_delegation(
            {
                "tenant_id": tenant_id,
                "request_id": request_id,
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "reason": reason,
                "expires_at": expires_at,
                "is_active": True,
            }
        )

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="approval.delegated",
            entity_type="approval_request",
            entity_id=request_id,
            tenant_id=tenant_id,
            user_id=from_user_id,
            metadata=EventMetadata(
                source="approval_service",
                version="1.0",
                additional_data={
                    "delegated_to": str(to_user_id),
                    "reason": reason,
                },
            ),
        )

        return delegation

    def get_approval_actions(
        self, request_id: UUID, tenant_id: UUID
    ) -> list[ApprovalAction]:
        """Get approval actions for a request."""
        return self.repository.get_approval_actions_by_request(request_id, tenant_id)

    def cancel_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ApprovalRequest:
        """Cancel an approval request."""
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        # Only allow cancelling pending requests
        if request.status != ApprovalStatus.PENDING:
            raise ValueError("Cannot cancel request that is not pending")

        # Update request status
        updated_request = self.repository.update_approval_request(
            request,
            {
                "status": ApprovalStatus.CANCELLED,
                "completed_at": datetime.now(UTC),
            },
        )

        # Publish event
        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="approval.cancelled",
            entity_type="approval_request",
            entity_id=updated_request.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="approval_service",
                version="1.0",
                additional_data={"request_title": updated_request.title},
            ),
        )

        return updated_request

    def get_delegations(
        self,
        request_id: UUID,
        tenant_id: UUID,
    ) -> list[ApprovalDelegation]:
        """Get delegations for a request."""
        return self.repository.get_approval_delegations(
            tenant_id=tenant_id,
            request_id=request_id,
        )

    def get_approval_stats(
        self,
        tenant_id: UUID,
    ) -> dict:
        """Get approval statistics."""
        # Get all requests for tenant
        all_requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            skip=0,
            limit=10000,
        )

        # Count by status
        status_counts = {}
        for request in all_requests:
            status = request.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate average approval time
        approved_requests = [
            r for r in all_requests
            if r.status == ApprovalStatus.APPROVED and r.completed_at
        ]
        avg_approval_time = None
        if approved_requests:
            total_time = sum(
                (r.completed_at - r.requested_at).total_seconds()
                for r in approved_requests
            )
            avg_approval_time = total_time / len(approved_requests)

        # Get most used flows
        flow_usage = {}
        for request in all_requests:
            flow_id = str(request.flow_id)
            flow_usage[flow_id] = flow_usage.get(flow_id, 0) + 1

        # Sort flows by usage
        top_flows = sorted(flow_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_requests": len(all_requests),
            "status_counts": status_counts,
            "avg_approval_time_seconds": avg_approval_time,
            "top_flows": [
                {"flow_id": flow_id, "request_count": count}
                for flow_id, count in top_flows
            ],
        }

    def get_request_timeline(
        self,
        request_id: UUID,
        tenant_id: UUID,
    ) -> list[dict]:
        """Get timeline of actions and delegations for a request."""
        # Get request
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        timeline = []

        # Add request creation event
        timeline.append({
            "type": "request_created",
            "timestamp": request.requested_at,
            "actor_id": str(request.requested_by),
            "data": {
                "title": request.title,
                "entity_type": request.entity_type,
                "entity_id": str(request.entity_id),
            },
        })

        # Get actions
        actions = self.repository.get_approval_actions_by_request(
            request_id, tenant_id
        )
        for action in actions:
            timeline.append({
                "type": "action",
                "action_type": action.action_type,
                "timestamp": action.acted_at,
                "actor_id": str(action.acted_by) if action.acted_by else None,
                "step_order": action.step_order,
                "comment": action.comment,
            })

        # Get delegations
        delegations = self.repository.get_approval_delegations(
            tenant_id=tenant_id,
            request_id=request_id,
        )
        for delegation in delegations:
            timeline.append({
                "type": "delegation",
                "timestamp": delegation.created_at,
                "actor_id": str(delegation.from_user_id),
                "data": {
                    "to_user_id": str(delegation.to_user_id),
                    "reason": delegation.reason,
                    "expires_at": delegation.expires_at.isoformat() if delegation.expires_at else None,
                },
            })

        # Add completion event if applicable
        if request.completed_at:
            timeline.append({
                "type": "completed",
                "timestamp": request.completed_at,
                "data": {
                    "status": request.status.value,
                },
            })

        # Sort by timestamp
        return sorted(timeline, key=lambda x: x["timestamp"])

    def get_or_create_request_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        auto_create: bool = False,
        flow_id: UUID | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> ApprovalRequest | None:
        """Get existing approval request or create new one for an entity.

        Args:
            entity_type: Type of entity (e.g., 'order', 'invoice')
            entity_id: ID of the entity
            tenant_id: Tenant ID
            user_id: User ID creating the request
            auto_create: Whether to create a new request if none exists
            flow_id: Flow ID to use when creating (required if auto_create=True)
            title: Title for the request (required if auto_create=True)
            description: Description for the request (optional)

        Returns:
            ApprovalRequest or None if not found and auto_create=False
        """
        # Try to find existing request
        existing_request = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            status="pending",
            skip=0,
            limit=1,
        )

        if existing_request:
            return existing_request[0]

        # Auto-create if requested
        if auto_create:
            if not flow_id:
                raise ValueError("flow_id is required when auto_create=True")
            if not title:
                raise ValueError("title is required when auto_create=True")

            # Verify flow exists
            flow = self.repository.get_approval_flow_by_id(flow_id, tenant_id)
            if not flow:
                raise ValueError("Approval flow not found")

            request = self.create_approval_request(
                request_data={
                    "flow_id": flow_id,
                    "title": title,
                    "description": description,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                },
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return request

        return None

    def get_request_widget_data(
        self,
        request_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Get all data needed for the approval widget in a single call.

        Args:
            request_id: Request ID
            tenant_id: Tenant ID
            user_id: Current user ID

        Returns:
            Dict containing request, current step, permissions, form schema, and timeline
        """
        # Get request
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        # Get flow
        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        # Get current step
        current_step = self.flow_engine.get_current_step(request, flow)

        # Check if user can approve
        can_approve = self.flow_engine.can_approve(request, user_id, flow) if current_step else False

        # Get timeline
        timeline = self.get_request_timeline(request_id, tenant_id)

        return {
            "request": {
                "id": str(request.id),
                "title": request.title,
                "description": request.description,
                "status": request.status.value,
                "current_step": request.current_step,
                "entity_type": request.entity_type,
                "entity_id": str(request.entity_id),
                "requested_by": str(request.requested_by) if request.requested_by else None,
                "requested_at": request.requested_at.isoformat(),
                "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            },
            "flow": {
                "id": str(flow.id),
                "name": flow.name,
                "flow_type": flow.flow_type,
            },
            "current_step": {
                "id": str(current_step.id) if current_step else None,
                "step_order": current_step.step_order if current_step else None,
                "name": current_step.name if current_step else None,
                "description": current_step.description if current_step else None,
                "approver_type": current_step.approver_type if current_step else None,
            } if current_step else None,
            "permissions": {
                "can_approve": can_approve,
            },
            "timeline": timeline,
        }

    def get_entity_approval_status(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """Get approval status for an entity without creating a request.

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            tenant_id: Tenant ID

        Returns:
            Dict containing status, current_step, and can_approve
        """
        # Try to find existing request
        requests = self.repository.get_approval_requests(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            skip=0,
            limit=1,
        )

        if not requests:
            return {
                "has_request": False,
                "status": None,
                "current_step": None,
                "request_id": None,
            }

        request = requests[0]
        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)

        return {
            "has_request": True,
            "status": request.status.value,
            "current_step": request.current_step,
            "request_id": str(request.id),
            "flow_name": flow.name if flow else None,
        }

    def user_can_approve_step(
        self,
        request_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """Check if a user can approve a specific request.

        Args:
            request_id: Request ID
            user_id: User ID to check
            tenant_id: Tenant ID

        Returns:
            Dict containing can_approve boolean and step information
        """
        # Get request
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        # Get flow
        flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        # Get current step
        current_step = self.flow_engine.get_current_step(request, flow)

        # Check if user can approve
        can_approve = self.flow_engine.can_approve(request, user_id, flow) if current_step else False

        return {
            "can_approve": can_approve,
            "current_step": {
                "id": str(current_step.id) if current_step else None,
                "step_order": current_step.step_order if current_step else None,
                "name": current_step.name if current_step else None,
                "description": current_step.description if current_step else None,
                "approver_type": current_step.approver_type if current_step else None,
                "rejection_required": current_step.rejection_required if current_step else False,
            } if current_step else None,
            "request_status": request.status.value,
        }

    def bulk_approve_requests(
        self,
        request_ids: list[UUID],
        tenant_id: UUID,
        user_id: UUID,
        comment: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[ApprovalRequest]:
        """Approve multiple approval requests."""
        results = []
        errors = []

        for request_id in request_ids:
            try:
                request = self.repository.get_approval_request_by_id(request_id, tenant_id)
                if not request:
                    errors.append(f"Request {request_id} not found")
                    continue

                # Get the flow for this request
                flow = self.repository.get_approval_flow_by_id(request.flow_id, tenant_id)
                if not flow:
                    errors.append(f"Flow {request.flow_id} not found for request {request_id}")
                    continue

                if not self.flow_engine.can_approve(request, user_id, flow):
                    errors.append(f"User cannot approve request {request_id}")
                    continue

                updated_request = self.flow_engine.process_approval(
                    request, user_id, "approve", comment, ip_address, user_agent
                )
                results.append(updated_request)

                # Publish event
                safe_publish_event(
                    event_publisher=self.event_publisher,
                    event_type="approval.approved",
                    entity_type="approval_request",
                    entity_id=updated_request.id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=EventMetadata(
                        source="approval_service",
                        version="1.0",
                        additional_data={"request_title": updated_request.title},
                    ),
                )
            except Exception as e:
                errors.append(f"Failed to approve request {request_id}: {str(e)}")

        if errors:
            logger.warning(f"Bulk approve completed with errors: {errors}")

        logger.info(f"Bulk approve results: {len(results)} approved, {len(errors)} errors")
        return results

    def bulk_reject_requests(
        self,
        request_ids: list[UUID],
        tenant_id: UUID,
        user_id: UUID,
        comment: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[ApprovalRequest]:
        """Reject multiple approval requests."""
        results = []
        errors = []

        for request_id in request_ids:
            try:
                request = self.repository.get_approval_request_by_id(request_id, tenant_id)
                if not request:
                    errors.append(f"Request {request_id} not found")
                    continue

                if not self.flow_engine.can_approve(request, user_id):
                    errors.append(f"User cannot reject request {request_id}")
                    continue

                updated_request = self.flow_engine.process_approval(
                    request, user_id, "reject", comment, ip_address, user_agent
                )
                results.append(updated_request)

                # Publish event
                safe_publish_event(
                    event_publisher=self.event_publisher,
                    event_type="approval.rejected",
                    entity_type="approval_request",
                    entity_id=updated_request.id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=EventMetadata(
                        source="approval_service",
                        version="1.0",
                        additional_data={"request_title": updated_request.title},
                    ),
                )
            except Exception as e:
                errors.append(f"Failed to reject request {request_id}: {str(e)}")

        if errors:
            logger.warning(f"Bulk reject completed with errors: {errors}")

        return results

    def _validate_conditions_json(self, conditions: dict) -> None:
        """Validate that conditions JSON has valid structure.

        Args:
            conditions: Conditions dictionary to validate

        Raises:
            ValueError: If conditions are invalid
        """
        if not isinstance(conditions, dict):
            raise ValueError("Conditions must be a dictionary")

        # Validate required fields
        if "rules" in conditions:
            if not isinstance(conditions["rules"], list):
                raise ValueError("Conditions rules must be a list")

            for rule in conditions["rules"]:
                if not isinstance(rule, dict):
                    raise ValueError("Each rule must be a dictionary")

                if "field" not in rule:
                    raise ValueError("Each rule must have a 'field'")

                if "operator" not in rule:
                    raise ValueError("Each rule must have an 'operator'")

                # Validate operator
                valid_operators = ["eq", "ne", "gt", "lt", "gte", "lte", "in", "not_in", "contains"]
                if rule["operator"] not in valid_operators:
                    raise ValueError(
                        f"Invalid operator '{rule['operator']}'. "
                        f"Valid operators: {', '.join(valid_operators)}"
                    )

                if "value" not in rule:
                    raise ValueError("Each rule must have a 'value'")

        # Validate logical operator
        if "logic" in conditions:
            if conditions["logic"] not in ["AND", "OR"]:
                raise ValueError("Logic must be either 'AND' or 'OR'")





