
"""Tenant repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tenant import Tenant


class TenantRepository:
    """Repository for tenant data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, tenant_data: dict) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        return (
            self.db.query(Tenant)
            .filter(Tenant.id == tenant_id)
            .first()
        )

    def get_by_slug(self, slug: str) -> Tenant | None:
        """Get tenant by slug."""
        return (
            self.db.query(Tenant)
            .filter(Tenant.slug == slug)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        """Get all tenants with pagination."""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def update(
        self, tenant: Tenant, tenant_data: dict
    ) -> Tenant:
        """Update tenant data."""
        for key, value in tenant_data.items():
            if value is not None:
                setattr(tenant, key, value)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def delete(self, tenant: Tenant) -> None:
        """Delete a tenant."""
        self.db.delete(tenant)
        self.db.commit()
