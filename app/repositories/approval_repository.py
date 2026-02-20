"""Approval repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.approval import (
    ApprovalAction,
    ApprovalDelegation,
    ApprovalFlow,
    ApprovalRequest,
    ApprovalStep,
)


class ApprovalRepository:
    """Repository for approval data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Approval Flow methods
    def create_approval_flow(self, flow_data: dict) -> ApprovalFlow:
        """Create a new approval flow."""
        flow = ApprovalFlow(**flow_data)
        self.db.add(flow)
        self.db.commit()
        self.db.refresh(flow)
        return flow

    def get_approval_flow_by_id(
        self, flow_id: UUID, tenant_id: UUID
    ) -> ApprovalFlow | None:
        """Get approval flow by ID and tenant, excluding soft-deleted flows."""
        return (
            self.db.query(ApprovalFlow)
            .filter(
                ApprovalFlow.id == flow_id,
                ApprovalFlow.tenant_id == tenant_id,
                ApprovalFlow.deleted_at.is_(None),
            )
            .first()
        )

    def get_approval_flows(
        self,
        tenant_id: UUID,
        module: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ApprovalFlow]:
        """Get approval flows with optional filters, excluding soft-deleted flows."""
        query = self.db.query(ApprovalFlow).filter(
            ApprovalFlow.tenant_id == tenant_id,
            ApprovalFlow.deleted_at.is_(None),
        )

        if module:
            query = query.filter(ApprovalFlow.module == module)
        if is_active is not None:
            query = query.filter(ApprovalFlow.is_active == is_active)

        return (
            query.order_by(ApprovalFlow.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_approval_flow(self, flow: ApprovalFlow, flow_data: dict) -> ApprovalFlow:
        """Update approval flow."""
        for key, value in flow_data.items():
            setattr(flow, key, value)
        self.db.commit()
        self.db.refresh(flow)
        return flow

    def delete_approval_flow(self, flow: ApprovalFlow) -> None:
        """Delete approval flow."""
        self.db.delete(flow)
        self.db.commit()

    # Approval Step methods
    def create_approval_step(self, step_data: dict) -> ApprovalStep:
        """Create a new approval step."""
        step = ApprovalStep(**step_data)
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_approval_step_by_id(
        self, step_id: UUID, tenant_id: UUID
    ) -> ApprovalStep | None:
        """Get approval step by ID."""
        return (
            self.db.query(ApprovalStep)
            .filter(ApprovalStep.id == step_id, ApprovalStep.tenant_id == tenant_id)
            .first()
        )

    def get_approval_steps_by_flow(
        self, flow_id: UUID, tenant_id: UUID
    ) -> list[ApprovalStep]:
        """Get approval steps by flow."""
        return (
            self.db.query(ApprovalStep)
            .filter(
                ApprovalStep.flow_id == flow_id, ApprovalStep.tenant_id == tenant_id
            )
            .order_by(ApprovalStep.step_order.asc())
            .all()
        )

    def update_approval_step(self, step: ApprovalStep, step_data: dict) -> ApprovalStep:
        """Update approval step."""
        for key, value in step_data.items():
            setattr(step, key, value)
        self.db.commit()
        self.db.refresh(step)
        return step

    def delete_approval_step(self, step: ApprovalStep) -> None:
        """Delete approval step."""
        self.db.delete(step)
        self.db.commit()

    def delete_all_approval_steps(self, flow_id: UUID, tenant_id: UUID) -> None:
        """Delete all approval steps for a given flow."""
        self.db.query(ApprovalStep).filter(
            ApprovalStep.flow_id == flow_id, ApprovalStep.tenant_id == tenant_id
        ).delete()
        self.db.commit()

    # Approval Request methods
    def create_approval_request(self, request_data: dict) -> ApprovalRequest:
        """Create a new approval request."""
        request = ApprovalRequest(**request_data)
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_approval_request_by_id(
        self, request_id: UUID, tenant_id: UUID
    ) -> ApprovalRequest | None:
        """Get approval request by ID and tenant."""
        return (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == request_id, ApprovalRequest.tenant_id == tenant_id
            )
            .first()
        )

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
        """Get approval requests with optional filters."""
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.tenant_id == tenant_id
        )

        if flow_id:
            query = query.filter(ApprovalRequest.flow_id == flow_id)
        if entity_type:
            query = query.filter(ApprovalRequest.entity_type == entity_type)
        if entity_id:
            query = query.filter(ApprovalRequest.entity_id == entity_id)
        if status:
            query = query.filter(ApprovalRequest.status == status)
        if requested_by:
            query = query.filter(ApprovalRequest.requested_by == requested_by)

        return (
            query.order_by(ApprovalRequest.requested_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_approval_request(
        self, request: ApprovalRequest, request_data: dict
    ) -> ApprovalRequest:
        """Update approval request."""
        for key, value in request_data.items():
            setattr(request, key, value)
        self.db.commit()
        self.db.refresh(request)
        return request

    def delete_approval_request(self, request: ApprovalRequest) -> None:
        """Delete approval request."""
        self.db.delete(request)
        self.db.commit()

    # Approval Action methods
    def create_approval_action(self, action_data: dict) -> ApprovalAction:
        """Create a new approval action."""
        action = ApprovalAction(**action_data)
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    def get_approval_actions_by_request(
        self, request_id: UUID, tenant_id: UUID
    ) -> list[ApprovalAction]:
        """Get approval actions by request."""
        return (
            self.db.query(ApprovalAction)
            .filter(
                ApprovalAction.request_id == request_id,
                ApprovalAction.tenant_id == tenant_id,
            )
            .order_by(ApprovalAction.acted_at.asc())
            .all()
        )

    # Approval Delegation methods
    def create_approval_delegation(self, delegation_data: dict) -> ApprovalDelegation:
        """Create a new approval delegation."""
        delegation = ApprovalDelegation(**delegation_data)
        self.db.add(delegation)
        self.db.commit()
        self.db.refresh(delegation)
        return delegation

    def get_approval_delegations(
        self,
        tenant_id: UUID,
        request_id: UUID | None = None,
        from_user_id: UUID | None = None,
        to_user_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> list[ApprovalDelegation]:
        """Get approval delegations with optional filters."""
        query = self.db.query(ApprovalDelegation).filter(
            ApprovalDelegation.tenant_id == tenant_id
        )

        if request_id:
            query = query.filter(ApprovalDelegation.request_id == request_id)
        if from_user_id:
            query = query.filter(ApprovalDelegation.from_user_id == from_user_id)
        if to_user_id:
            query = query.filter(ApprovalDelegation.to_user_id == to_user_id)
        if is_active is not None:
            query = query.filter(ApprovalDelegation.is_active == is_active)

        return query.all()

    def update_approval_delegation(
        self, delegation: ApprovalDelegation, delegation_data: dict
    ) -> ApprovalDelegation:
        """Update approval delegation."""
        for key, value in delegation_data.items():
            setattr(delegation, key, value)
        self.db.commit()
        self.db.refresh(delegation)
        return delegation

    def delete_approval_delegation(self, delegation: ApprovalDelegation) -> None:
        """Delete approval delegation."""
        self.db.delete(delegation)
        self.db.commit()
