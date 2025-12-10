"""Contact method repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contact_method import ContactMethod, EntityType


class ContactMethodRepository:
    """Repository for contact method data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, contact_method_data: dict) -> ContactMethod:
        """Create a new contact method."""
        contact_method = ContactMethod(**contact_method_data)
        self.db.add(contact_method)
        self.db.commit()
        self.db.refresh(contact_method)
        return contact_method

    def get_by_id(self, contact_method_id: UUID) -> ContactMethod | None:
        """Get contact method by ID."""
        return (
            self.db.query(ContactMethod)
            .filter(ContactMethod.id == contact_method_id)
            .first()
        )

    def get_by_entity(
        self, entity_type: EntityType | str, entity_id: UUID
    ) -> list[ContactMethod]:
        """Get all contact methods for an entity."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)
        return (
            self.db.query(ContactMethod)
            .filter(
                ContactMethod.entity_type == entity_type,
                ContactMethod.entity_id == entity_id,
            )
            .all()
        )

    def get_primary_contact_method(
        self,
        entity_type: EntityType | str,
        entity_id: UUID,
        method_type: str | None = None,
    ) -> ContactMethod | None:
        """Get primary contact method for an entity, optionally filtered by method_type."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)
        query = self.db.query(ContactMethod).filter(
            ContactMethod.entity_type == entity_type,
            ContactMethod.entity_id == entity_id,
            ContactMethod.is_primary == True,  # noqa: E712
        )
        if method_type:
            from app.models.contact_method import ContactMethodType

            if isinstance(method_type, str):
                method_type = ContactMethodType(method_type)
            query = query.filter(ContactMethod.method_type == method_type)
        return query.first()

    def update(
        self, contact_method: ContactMethod, contact_method_data: dict
    ) -> ContactMethod:
        """Update contact method data."""
        for key, value in contact_method_data.items():
            if value is not None:
                setattr(contact_method, key, value)
        self.db.commit()
        self.db.refresh(contact_method)
        return contact_method

    def set_primary_contact_method(
        self,
        entity_type: EntityType | str,
        entity_id: UUID,
        contact_method_id: UUID,
        method_type: str | None = None,
    ) -> None:
        """Set a contact method as primary, unsetting others of the same type."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)

        # Unset all primary methods of the same type (if method_type specified)
        # or all primary methods (if method_type not specified)
        query = self.db.query(ContactMethod).filter(
            ContactMethod.entity_type == entity_type,
            ContactMethod.entity_id == entity_id,
            ContactMethod.is_primary == True,  # noqa: E712
        )
        if method_type:
            from app.models.contact_method import ContactMethodType

            if isinstance(method_type, str):
                method_type = ContactMethodType(method_type)
            query = query.filter(ContactMethod.method_type == method_type)

        for cm in query.all():
            cm.is_primary = False

        # Set the specified contact method as primary
        contact_method = self.get_by_id(contact_method_id)
        if contact_method:
            contact_method.is_primary = True

        self.db.commit()

    def delete(self, contact_method: ContactMethod) -> None:
        """Delete a contact method."""
        self.db.delete(contact_method)
        self.db.commit()
