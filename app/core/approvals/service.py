"""Approval service for approval workflow management."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher, get_event_publisher
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
        """Get the next step in the approval flow."""
        steps = self.repository.get_approval_steps_by_flow(flow.id, request.tenant_id)
        if not steps:
            return None

        # Get current step
        current_step_order = request.current_step
        next_step = next(
            (s for s in steps if s.step_order > current_step_order), None
        )

        return next_step

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
            # TODO: Check if user has the role
            return False
        elif current_step.approver_type == "dynamic":
            # TODO: Evaluate dynamic rule
            return False

        return False

    def process_approval(
        self,
        request: ApprovalRequest,
        user_id: UUID,
        action_type: str,
        comment: str | None = None,
    ) -> ApprovalRequest:
        """Process an approval action."""
        flow = self.repository.get_approval_flow_by_id(request.flow_id, request.tenant_id)
        if not flow:
            raise ValueError("Approval flow not found")

        current_step = self.get_current_step(request, flow)
        if not current_step:
            raise ValueError("Current step not found")

        # Create action
        action = self.repository.create_approval_action(
            {
                "tenant_id": request.tenant_id,
                "request_id": request.id,
                "action_type": action_type,
                "step_order": current_step.step_order,
                "comment": comment,
                "acted_by": user_id,
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
                # Check if all required approvals are met
                # For now, just mark as approved if action is approve
                # TODO: Implement proper parallel approval logic
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


class ApprovalService:
    """Service for managing approval workflows."""

    def __init__(
        self,
        db: Session,
        task_service: TaskService | None = None,
        notification_service: NotificationService | None = None,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize approval service.

        Args:
            db: Database session
            task_service: TaskService instance (for creating tasks)
            notification_service: NotificationService instance
            event_publisher: EventPublisher instance
        """
        self.db = db
        self.repository = ApprovalRepository(db)
        self.flow_engine = FlowEngine(db)
        self.task_service = task_service
        self.notification_service = notification_service or NotificationService(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def create_approval_flow(
        self,
        flow_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ApprovalFlow:
        """Create a new approval flow."""
        flow_data["tenant_id"] = tenant_id
        flow_data["created_by"] = user_id

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

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
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
                )
        except Exception as e:
            logger.error(f"Failed to publish approval.requested event: {e}")

        return request

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
    ) -> ApprovalRequest:
        """Approve an approval request."""
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        updated_request = self.flow_engine.process_approval(
            request, user_id, "approve", comment
        )

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
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
                )
        except Exception as e:
            logger.error(f"Failed to publish approval.approved event: {e}")

        return updated_request

    def reject_request(
        self,
        request_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        comment: str | None = None,
    ) -> ApprovalRequest:
        """Reject an approval request."""
        request = self.repository.get_approval_request_by_id(request_id, tenant_id)
        if not request:
            raise ValueError("Approval request not found")

        updated_request = self.flow_engine.process_approval(
            request, user_id, "reject", comment
        )

        # Publish event
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
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
                )
        except Exception as e:
            logger.error(f"Failed to publish approval.rejected event: {e}")

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
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self.event_publisher.publish(
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
                )
            else:
                loop.run_until_complete(
                    self.event_publisher.publish(
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
                )
        except Exception as e:
            logger.error(f"Failed to publish approval.delegated event: {e}")

        return delegation

    def get_approval_actions(
        self, request_id: UUID, tenant_id: UUID
    ) -> list[ApprovalAction]:
        """Get approval actions for a request."""
        return self.repository.get_approval_actions_by_request(request_id, tenant_id)

    def get_approval_delegations(
        self,
        tenant_id: UUID,
        request_id: UUID | None = None,
        from_user_id: UUID | None = None,
        to_user_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> list[ApprovalDelegation]:
        """Get approval delegations."""
        return self.repository.get_approval_delegations(
            tenant_id, request_id, from_user_id, to_user_id, is_active
        )

