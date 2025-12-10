
"""Contact repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contact import Contact


class ContactRepository:
    """Repository for contact data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, contact_data: dict) -> Contact:
        """Create a new contact."""
        contact = Contact(**contact_data)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_by_id(self, contact_id: UUID, tenant_id: UUID) -> Contact | None:
        """Get contact by ID, filtered by tenant."""
        return (
            self.db.query(Contact)
            .filter(Contact.id == contact_id, Contact.tenant_id == tenant_id)
            .first()
        )

    def get_all(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Contact]:
        """Get all contacts for a tenant with pagination."""
        return (
            self.db.query(Contact)
            .filter(Contact.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_organization(
        self,
        organization_id: UUID,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Contact]:
        """Get all contacts for an organization."""
        return (
            self.db.query(Contact)
            .filter(
                Contact.organization_id == organization_id,
                Contact.tenant_id == tenant_id,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_primary_contact(
        self, organization_id: UUID, tenant_id: UUID
    ) -> Contact | None:
        """Get primary contact for an organization."""
        return (
            self.db.query(Contact)
            .filter(
                Contact.organization_id == organization_id,
                Contact.tenant_id == tenant_id,
                Contact.is_primary_contact == True,  # noqa: E712
            )
            .first()
        )

    def update(self, contact: Contact, contact_data: dict) -> Contact:
        """Update contact data."""
        for key, value in contact_data.items():
            if value is not None:
                setattr(contact, key, value)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete(self, contact: Contact) -> None:
        """Delete a contact."""
        self.db.delete(contact)
        self.db.commit()
