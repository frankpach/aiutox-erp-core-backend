"""Calendar resource service for managing resources (rooms, equipment, users)."""

from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.models.calendar import CalendarResource, EventResource


class CalendarResourceService:
    """Service for managing calendar resources."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session."""
        self.db = db

    def create_resource(
        self,
        resource_data: dict,
        tenant_id: UUID,
    ) -> CalendarResource:
        """Create a new calendar resource.

        Args:
            resource_data: Resource data dictionary
            tenant_id: Tenant ID

        Returns:
            Created CalendarResource instance

        Raises:
            APIException: If resource creation fails
        """
        resource = CalendarResource(
            tenant_id=tenant_id,
            **resource_data,
        )

        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)

        return resource

    def get_resource(
        self,
        resource_id: UUID,
        tenant_id: UUID,
    ) -> CalendarResource | None:
        """Get a resource by ID.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID

        Returns:
            CalendarResource instance or None if not found
        """
        return (
            self.db.query(CalendarResource)
            .filter(
                and_(
                    CalendarResource.id == resource_id,
                    CalendarResource.tenant_id == tenant_id,
                )
            )
            .first()
        )

    def get_resources(
        self,
        tenant_id: UUID,
        calendar_id: UUID | None = None,
        resource_type: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CalendarResource]:
        """Get resources with optional filters.

        Args:
            tenant_id: Tenant ID
            calendar_id: Optional calendar ID filter
            resource_type: Optional resource type filter
            is_active: Optional active status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of CalendarResource instances
        """
        query = self.db.query(CalendarResource).filter(
            CalendarResource.tenant_id == tenant_id
        )

        if calendar_id is not None:
            query = query.filter(CalendarResource.calendar_id == calendar_id)

        if resource_type is not None:
            query = query.filter(CalendarResource.resource_type == resource_type)

        if is_active is not None:
            query = query.filter(CalendarResource.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def count_resources(
        self,
        tenant_id: UUID,
        calendar_id: UUID | None = None,
        resource_type: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count resources with optional filters.

        Args:
            tenant_id: Tenant ID
            calendar_id: Optional calendar ID filter
            resource_type: Optional resource type filter
            is_active: Optional active status filter

        Returns:
            Count of matching resources
        """
        query = self.db.query(CalendarResource).filter(
            CalendarResource.tenant_id == tenant_id
        )

        if calendar_id is not None:
            query = query.filter(CalendarResource.calendar_id == calendar_id)

        if resource_type is not None:
            query = query.filter(CalendarResource.resource_type == resource_type)

        if is_active is not None:
            query = query.filter(CalendarResource.is_active == is_active)

        return query.count()

    def update_resource(
        self,
        resource_id: UUID,
        tenant_id: UUID,
        resource_data: dict,
    ) -> CalendarResource | None:
        """Update a resource.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID
            resource_data: Resource data to update

        Returns:
            Updated CalendarResource instance or None if not found
        """
        resource = self.get_resource(resource_id, tenant_id)
        if not resource:
            return None

        for key, value in resource_data.items():
            if hasattr(resource, key):
                setattr(resource, key, value)

        self.db.commit()
        self.db.refresh(resource)

        return resource

    def delete_resource(
        self,
        resource_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Delete a resource.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        resource = self.get_resource(resource_id, tenant_id)
        if not resource:
            return False

        self.db.delete(resource)
        self.db.commit()

        return True

    def assign_resource_to_event(
        self,
        event_id: UUID,
        resource_id: UUID,
        tenant_id: UUID,
    ) -> EventResource:
        """Assign a resource to an event.

        Args:
            event_id: Event ID
            resource_id: Resource ID
            tenant_id: Tenant ID

        Returns:
            Created EventResource instance

        Raises:
            APIException: If assignment already exists
        """
        # Check if assignment already exists
        existing = (
            self.db.query(EventResource)
            .filter(
                and_(
                    EventResource.event_id == event_id,
                    EventResource.resource_id == resource_id,
                    EventResource.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if existing:
            raise APIException(
                code="RESOURCE_ALREADY_ASSIGNED",
                message="Resource is already assigned to this event",
                status_code=409,
            )

        event_resource = EventResource(
            tenant_id=tenant_id,
            event_id=event_id,
            resource_id=resource_id,
        )

        self.db.add(event_resource)
        self.db.commit()
        self.db.refresh(event_resource)

        return event_resource

    def get_event_resources(
        self,
        event_id: UUID,
        tenant_id: UUID,
    ) -> list[EventResource]:
        """Get all resources assigned to an event.

        Args:
            event_id: Event ID
            tenant_id: Tenant ID

        Returns:
            List of EventResource instances
        """
        return (
            self.db.query(EventResource)
            .filter(
                and_(
                    EventResource.event_id == event_id,
                    EventResource.tenant_id == tenant_id,
                )
            )
            .all()
        )

    def remove_resource_from_event(
        self,
        event_id: UUID,
        resource_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Remove a resource from an event.

        Args:
            event_id: Event ID
            resource_id: Resource ID
            tenant_id: Tenant ID

        Returns:
            True if removed, False if not found
        """
        event_resource = (
            self.db.query(EventResource)
            .filter(
                and_(
                    EventResource.event_id == event_id,
                    EventResource.resource_id == resource_id,
                    EventResource.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not event_resource:
            return False

        self.db.delete(event_resource)
        self.db.commit()

        return True

    def check_resource_availability(
        self,
        resource_id: UUID,
        tenant_id: UUID,
        start_time: str,
        end_time: str,
        exclude_event_id: UUID | None = None,
    ) -> bool:
        """Check if a resource is available in a time range.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            exclude_event_id: Optional event ID to exclude from check

        Returns:
            True if available, False if busy
        """
        from app.models.calendar import CalendarEvent

        query = (
            self.db.query(EventResource)
            .join(CalendarEvent, EventResource.event_id == CalendarEvent.id)
            .filter(
                and_(
                    EventResource.resource_id == resource_id,
                    EventResource.tenant_id == tenant_id,
                    CalendarEvent.start_time < end_time,
                    CalendarEvent.end_time > start_time,
                    CalendarEvent.status != "cancelled",
                )
            )
        )

        if exclude_event_id:
            query = query.filter(EventResource.event_id != exclude_event_id)

        conflicting_assignments = query.count()

        return conflicting_assignments == 0
