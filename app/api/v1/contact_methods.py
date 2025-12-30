"""Contact methods router for CRUD operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import raise_not_found
from app.models.user import User
from app.repositories.contact_method_repository import ContactMethodRepository
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.contact_method import (
    ContactMethodCreate,
    ContactMethodResponse,
    ContactMethodUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=StandardListResponse[ContactMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="List contact methods",
    description="List all contact methods for an entity. Requires auth.manage_users permission.",
)
async def list_contact_methods(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    entity_type: str = Query(..., description="Entity type: user, contact, organization, etc."),
    entity_id: UUID = Query(..., description="Entity ID"),
) -> StandardListResponse[ContactMethodResponse]:
    """
    List all contact methods for an entity.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        entity_type: Entity type (user, contact, organization, etc.).
        entity_id: Entity ID.

    Returns:
        StandardListResponse with list of contact methods.
    """
    repository = ContactMethodRepository(db)
    contact_methods = repository.get_by_entity(entity_type, entity_id)

    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Found {len(contact_methods)} contact methods for entity_type={entity_type}, entity_id={entity_id}")

    # Convert SQLAlchemy models to Pydantic models using from_attributes
    # This should handle enum conversion automatically
    try:
        response_data = [
            ContactMethodResponse.model_validate(cm, from_attributes=True)
            for cm in contact_methods
        ]
        logger.info(f"Successfully converted {len(response_data)} contact methods")
        return StandardListResponse(
            data=response_data,
            meta=PaginationMeta(
                total=len(response_data),
                page=1,
                page_size=len(response_data) if response_data else 1,
                total_pages=1,
            ),
        )
    except Exception as e:
        logger.error(f"Error in list_contact_methods: {e}", exc_info=True)
        # Fallback: try manual conversion if model_validate fails
        response_data = []
        for cm in contact_methods:
            try:
                # Manual conversion with enum handling
                cm_dict = {
                    "id": cm.id,
                    "entity_type": cm.entity_type.value if hasattr(cm.entity_type, 'value') else str(cm.entity_type),
                    "entity_id": cm.entity_id,
                    "method_type": cm.method_type.value if hasattr(cm.method_type, 'value') else str(cm.method_type),
                    "value": cm.value,
                    "label": cm.label,
                    "is_primary": cm.is_primary,
                    "is_verified": cm.is_verified,
                    "verified_at": cm.verified_at,
                    "notes": cm.notes,
                    "address_line1": cm.address_line1,
                    "address_line2": cm.address_line2,
                    "city": cm.city,
                    "state_province": cm.state_province,
                    "postal_code": cm.postal_code,
                    "country": cm.country,
                    "created_at": cm.created_at,
                    "updated_at": cm.updated_at,
                }
                response_data.append(ContactMethodResponse.model_validate(cm_dict))
            except Exception as conv_error:
                logger.error(f"Error converting contact method {cm.id}: {conv_error}")
                continue
        return StandardListResponse(
            data=response_data,
            meta=PaginationMeta(
                total=len(response_data),
                page=1,
                page_size=len(response_data) if response_data else 1,
                total_pages=1,
            ),
        )


@router.get(
    "/{contact_method_id}",
    response_model=StandardResponse[ContactMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="Get contact method",
    description="Get a contact method by ID. Requires auth.manage_users permission.",
)
async def get_contact_method(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    contact_method_id: UUID,
) -> StandardResponse[ContactMethodResponse]:
    """
    Get a contact method by ID.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        contact_method_id: Contact method ID.

    Returns:
        StandardResponse with contact method data.

    Raises:
        APIException: If contact method not found.
    """
    repository = ContactMethodRepository(db)
    contact_method = repository.get_by_id(contact_method_id)

    if not contact_method:
        raise_not_found("Contact method not found")

    return StandardResponse(data=ContactMethodResponse.model_validate(contact_method, from_attributes=True))


@router.post(
    "",
    response_model=StandardResponse[ContactMethodResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create contact method",
    description="Create a new contact method. Requires auth.manage_users permission.",
)
async def create_contact_method(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    data: ContactMethodCreate,
) -> StandardResponse[ContactMethodResponse]:
    """
    Create a new contact method.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        data: Contact method creation data.

    Returns:
        StandardResponse with created contact method data.
    """
    repository = ContactMethodRepository(db)

    # Convert Pydantic model to dict, excluding None values for address fields if not address type
    contact_method_data = data.model_dump(exclude_none=True)

    # Convert enum strings to enum values for SQLAlchemy
    from app.models.contact_method import ContactMethodType, EntityType

    if "method_type" in contact_method_data:
        if isinstance(contact_method_data["method_type"], str):
            contact_method_data["method_type"] = ContactMethodType(contact_method_data["method_type"])

    if "entity_type" in contact_method_data:
        if isinstance(contact_method_data["entity_type"], str):
            contact_method_data["entity_type"] = EntityType(contact_method_data["entity_type"])

    # Create the contact method first
    contact_method = repository.create(contact_method_data)

    # If setting as primary, unset other primary methods of the same type and set this one as primary
    if contact_method_data.get("is_primary", False):
        repository.set_primary_contact_method(
            entity_type=contact_method.entity_type,
            entity_id=contact_method.entity_id,
            contact_method_id=contact_method.id,
            method_type=contact_method.method_type.value if hasattr(contact_method.method_type, 'value') else str(contact_method.method_type),
        )
        # Refresh to get updated is_primary status
        db.refresh(contact_method)

    return StandardResponse(data=ContactMethodResponse.model_validate(contact_method, from_attributes=True))


@router.patch(
    "/{contact_method_id}",
    response_model=StandardResponse[ContactMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="Update contact method",
    description="Update a contact method. Requires auth.manage_users permission.",
)
async def update_contact_method(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    contact_method_id: UUID,
    data: ContactMethodUpdate,
) -> StandardResponse[ContactMethodResponse]:
    """
    Update a contact method.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        contact_method_id: Contact method ID.
        data: Contact method update data.

    Returns:
        StandardResponse with updated contact method data.

    Raises:
        APIException: If contact method not found.
    """
    repository = ContactMethodRepository(db)
    contact_method = repository.get_by_id(contact_method_id)

    if not contact_method:
        raise_not_found("Contact method not found")

    # Convert Pydantic model to dict, excluding None values
    update_data = data.model_dump(exclude_none=True)

    # If setting as primary, unset other primary methods
    if update_data.get("is_primary"):
        repository.set_primary_contact_method(
            entity_type=contact_method.entity_type,
            entity_id=contact_method.entity_id,
            contact_method_id=contact_method_id,
            method_type=contact_method.method_type.value if hasattr(contact_method.method_type, 'value') else str(contact_method.method_type),
        )

    updated_contact_method = repository.update(contact_method, update_data)

    return StandardResponse(data=ContactMethodResponse.model_validate(updated_contact_method, from_attributes=True))


@router.delete(
    "/{contact_method_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete contact method",
    description="Delete a contact method. Requires auth.manage_users permission.",
)
async def delete_contact_method(
    current_user: Annotated[User, Depends(require_permission("auth.manage_users"))],
    db: Annotated[Session, Depends(get_db)],
    contact_method_id: UUID,
) -> StandardResponse[dict]:
    """
    Delete a contact method.

    Requires: auth.manage_users

    Args:
        current_user: Current authenticated user (must have auth.manage_users).
        db: Database session.
        contact_method_id: Contact method ID.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If contact method not found.
    """
    repository = ContactMethodRepository(db)
    contact_method = repository.get_by_id(contact_method_id)

    if not contact_method:
        raise_not_found("Contact method not found")

    repository.delete(contact_method)

    return StandardResponse(data={"message": "Contact method deleted successfully"})

