"""
Seeder for predefined saved filters in the Users module.
Creates common filters that users can use immediately.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.view import SavedFilter


def seed_saved_filters(db: Session, tenant_id: str) -> None:
    """
    Create predefined saved filters for the Users module.

    Args:
        db: Database session
        tenant_id: Tenant ID for multi-tenancy
    """
    # Get system user or first admin user for created_by
    system_user = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.email.like("admin@%"))
        .first()
    )
    created_by = system_user.id if system_user else None

    predefined_filters = [
        {
            "name": "Usuarios Activos",
            "description": "Muestra solo usuarios con estado activo",
            "module": "users",
            "filters": {"is_active": {"operator": "eq", "value": True}},
            "is_default": True,  # This will be the default filter
            "is_shared": True,
        },
        {
            "name": "Email No Verificado",
            "description": "Usuarios que no han verificado su email",
            "module": "users",
            "filters": {"email_verified_at": {"operator": "is_null", "value": None}},
            "is_default": False,
            "is_shared": True,
        },
        {
            "name": "Sin Acceso Reciente",
            "description": "Usuarios que no han iniciado sesión en los últimos 30 días",
            "module": "users",
            "filters": {
                "last_login_at": {
                    "operator": "lt",
                    "value": (
                        datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
                    ).isoformat(),
                }
            },
            "is_default": False,
            "is_shared": True,
        },
        {
            "name": "Usuarios Inactivos",
            "description": "Usuarios con estado inactivo",
            "module": "users",
            "filters": {"is_active": {"operator": "eq", "value": False}},
            "is_default": False,
            "is_shared": True,
        },
        {
            "name": "Con Autenticación de Dos Factores",
            "description": "Usuarios que tienen 2FA habilitado",
            "module": "users",
            "filters": {"two_factor_enabled": {"operator": "eq", "value": True}},
            "is_default": False,
            "is_shared": True,
        },
        {
            "name": "Usuarios Creados Este Mes",
            "description": "Usuarios creados en el último mes",
            "module": "users",
            "filters": {
                "created_at": {
                    "operator": "gte",
                    "value": (
                        datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
                    ).isoformat(),
                }
            },
            "is_default": False,
            "is_shared": True,
        },
    ]

    # Check if filters already exist for this tenant
    existing_filters = (
        db.query(SavedFilter)
        .filter(SavedFilter.tenant_id == tenant_id, SavedFilter.module == "users")
        .all()
    )

    if existing_filters:
        # Filters already seeded, skip
        return

    # Create predefined filters
    for filter_data in predefined_filters:
        saved_filter = SavedFilter(
            id=uuid4(),
            tenant_id=tenant_id,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            **filter_data,
        )
        db.add(saved_filter)

    db.commit()


def clear_saved_filters(db: Session, tenant_id: str) -> None:
    """
    Clear all predefined saved filters for a tenant (useful for testing).

    Args:
        db: Database session
        tenant_id: Tenant ID
    """
    db.query(SavedFilter).filter(
        SavedFilter.tenant_id == tenant_id, SavedFilter.module == "users"
    ).delete()
    db.commit()
