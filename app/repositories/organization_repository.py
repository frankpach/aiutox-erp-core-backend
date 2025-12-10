"""Organization repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.organization import Organization


class OrganizationRepository:
    """Repository for organization (business entities) data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, organization_data: dict) -> Organization:
        """Create a new organization."""
        organization = Organization(**organization_data)
        self.db.add(organization)
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def get_by_id(self, organization_id: UUID, tenant_id: UUID) -> Organization | None:
        """Get organization by ID, filtered by tenant."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.id == organization_id,
                Organization.tenant_id == tenant_id,
            )
            .first()
        )

    def get_by_tax_id(self, tax_id: str, tenant_id: UUID) -> Organization | None:
        """Get organization by tax_id, filtered by tenant."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.tax_id == tax_id,
                Organization.tenant_id == tenant_id,
            )
            .first()
        )

    def get_all(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        """Get all organizations for a tenant with pagination."""
        return (
            self.db.query(Organization)
            .filter(Organization.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_type(
        self,
        tenant_id: UUID,
        organization_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Organization]:
        """Get organizations by type for a tenant."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.tenant_id == tenant_id,
                Organization.organization_type == organization_type,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_organization_contacts(
        self, organization_id: UUID, tenant_id: UUID
    ) -> list:
        """Get all contacts for an organization."""
        from app.models.contact import Contact

        return (
            self.db.query(Contact)
            .filter(
                Contact.organization_id == organization_id,
                Contact.tenant_id == tenant_id,
            )
            .all()
        )

    def update(
        self, organization: Organization, organization_data: dict
    ) -> Organization:
        """Update organization data."""
        for key, value in organization_data.items():
            if value is not None:
                setattr(organization, key, value)
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def delete(self, organization: Organization) -> None:
        """Delete an organization."""
        self.db.delete(organization)
        self.db.commit()
