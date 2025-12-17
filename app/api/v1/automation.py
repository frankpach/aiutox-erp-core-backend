"""Automation router for rule management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.automation.engine import AutomationEngine
from app.core.automation.service import AutomationService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import Event, EventMetadata
from app.models.user import User
from app.schemas.automation import (
    ActionSchema,
    AutomationExecutionResponse,
    ConditionSchema,
    RuleCreate,
    RuleResponse,
    RuleUpdate,
    TriggerSchema,
)
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


def get_automation_service(db: Annotated[Session, Depends(get_db)]) -> AutomationService:
    """Dependency to get AutomationService."""
    return AutomationService(db)


def get_automation_engine(db: Annotated[Session, Depends(get_db)]) -> AutomationEngine:
    """Dependency to get AutomationEngine."""
    return AutomationEngine(db)


@router.post(
    "/rules",
    response_model=StandardResponse[RuleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create automation rule",
    description="Create a new automation rule. Requires automation.manage permission.",
)
async def create_rule(
    rule_data: RuleCreate,
    current_user: Annotated[User, Depends(require_permission("automation.manage"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
) -> StandardResponse[RuleResponse]:
    """Create a new automation rule."""
    # Convert Pydantic models to dicts for storage
    trigger_dict = rule_data.trigger.model_dump()
    conditions_dict = (
        [c.model_dump() for c in rule_data.conditions] if rule_data.conditions else None
    )
    actions_dict = [a.model_dump() for a in rule_data.actions]

    rule = service.create_rule(
        tenant_id=current_user.tenant_id,
        name=rule_data.name,
        description=rule_data.description,
        trigger=trigger_dict,
        conditions=conditions_dict,
        actions=actions_dict,
        enabled=rule_data.enabled,
    )

    return StandardResponse(
        data=RuleResponse.model_validate(rule),
        message="Rule created successfully",
    )


@router.get(
    "/rules",
    response_model=StandardListResponse[RuleResponse],
    status_code=status.HTTP_200_OK,
    summary="List automation rules",
    description="List all automation rules for the current tenant. Requires automation.view permission.",
)
async def list_rules(
    current_user: Annotated[User, Depends(require_permission("automation.view"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    enabled_only: bool = Query(default=False, description="Only return enabled rules"),
) -> StandardListResponse[RuleResponse]:
    """List all automation rules."""
    skip = (page - 1) * page_size
    rules = service.get_all_rules(
        tenant_id=current_user.tenant_id, enabled_only=enabled_only, skip=skip, limit=page_size
    )

    total = len(rules)  # TODO: Add count method to repository
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[RuleResponse.model_validate(rule) for rule in rules],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        message="Rules retrieved successfully",
    )


@router.get(
    "/rules/{rule_id}",
    response_model=StandardResponse[RuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get automation rule",
    description="Get a specific automation rule by ID. Requires automation.view permission.",
)
async def get_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(require_permission("automation.view"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
) -> StandardResponse[RuleResponse]:
    """Get a specific automation rule."""
    rule = service.get_rule(rule_id, current_user.tenant_id)
    if not rule:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTOMATION_RULE_NOT_FOUND",
            message=f"Rule with ID {rule_id} not found",
        )

    return StandardResponse(
        data=RuleResponse.model_validate(rule),
        message="Rule retrieved successfully",
    )


@router.put(
    "/rules/{rule_id}",
    response_model=StandardResponse[RuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Update automation rule",
    description="Update an automation rule. Requires automation.manage permission.",
)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdate,
    current_user: Annotated[User, Depends(require_permission("automation.manage"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
) -> StandardResponse[RuleResponse]:
    """Update an automation rule."""
    # Convert Pydantic models to dicts if provided
    trigger_dict = rule_data.trigger.model_dump() if rule_data.trigger else None
    conditions_dict = (
        [c.model_dump() for c in rule_data.conditions] if rule_data.conditions else None
    )
    actions_dict = [a.model_dump() for a in rule_data.actions] if rule_data.actions else None

    rule = service.update_rule(
        rule_id=rule_id,
        tenant_id=current_user.tenant_id,
        name=rule_data.name,
        description=rule_data.description,
        trigger=trigger_dict,
        conditions=conditions_dict,
        actions=actions_dict,
        enabled=rule_data.enabled,
    )

    if not rule:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTOMATION_RULE_NOT_FOUND",
            message=f"Rule with ID {rule_id} not found",
        )

    return StandardResponse(
        data=RuleResponse.model_validate(rule),
        message="Rule updated successfully",
    )


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete automation rule",
    description="Delete an automation rule. Requires automation.manage permission.",
)
async def delete_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(require_permission("automation.manage"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
) -> None:
    """Delete an automation rule."""
    deleted = service.delete_rule(rule_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTOMATION_RULE_NOT_FOUND",
            message=f"Rule with ID {rule_id} not found",
        )


@router.post(
    "/rules/{rule_id}/execute",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Execute automation rule manually",
    description="Execute an automation rule manually with a test event. Requires automation.manage permission.",
)
async def execute_rule(
    rule_id: UUID,
    current_user: Annotated[User, Depends(require_permission("automation.manage"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
    engine: Annotated[AutomationEngine, Depends(get_automation_engine)],
    event_type: str = Query(..., description="Event type to simulate"),
    entity_type: str = Query(..., description="Entity type"),
    entity_id: UUID = Query(..., description="Entity ID"),
) -> StandardResponse[dict[str, Any]]:
    """Execute an automation rule manually."""
    rule = service.get_rule(rule_id, current_user.tenant_id)
    if not rule:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTOMATION_RULE_NOT_FOUND",
            message=f"Rule with ID {rule_id} not found",
        )

    # Create a test event
    test_event = Event(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        metadata=EventMetadata(
            source="automation_service",
            version="1.0",
            additional_data={"manual_execution": True},
        ),
    )

    execution = await engine.execute_rule(rule, test_event)

    return StandardResponse(
        data={
            "execution_id": str(execution.id),
            "status": execution.status,
            "result": execution.result,
        },
        message="Rule executed successfully",
    )


@router.get(
    "/rules/{rule_id}/executions",
    response_model=StandardListResponse[AutomationExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get rule execution history",
    description="Get execution history for a rule. Requires automation.view permission.",
)
async def get_rule_executions(
    rule_id: UUID,
    current_user: Annotated[User, Depends(require_permission("automation.view"))],
    service: Annotated[AutomationService, Depends(get_automation_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[AutomationExecutionResponse]:
    """Get execution history for a rule."""
    # Verify rule exists and belongs to tenant
    rule = service.get_rule(rule_id, current_user.tenant_id)
    if not rule:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="AUTOMATION_RULE_NOT_FOUND",
            message=f"Rule with ID {rule_id} not found",
        )

    skip = (page - 1) * page_size
    executions = service.get_executions(rule_id, skip=skip, limit=page_size)

    total = len(executions)  # TODO: Add count method to repository
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[AutomationExecutionResponse.model_validate(ex) for ex in executions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Executions retrieved successfully",
    )







