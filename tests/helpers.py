"""Helper functions for tests."""

from uuid import UUID

from app.models.module_role import ModuleRole
from app.models.user import User
from app.services.auth_service import AuthService
from sqlalchemy.orm import Session


def create_user_with_permission(
    db_session: Session,
    user: User,
    module: str,
    role_name: str = "manager",
) -> dict[str, str]:
    """
    Create a module role for a user and return updated auth headers.

    Args:
        db_session: Database session.
        user: User object.
        module: Module name (e.g., "tasks", "files").
        role_name: Role name (e.g., "manager", "viewer", "editor").

    Returns:
        Dictionary with Authorization header containing updated token.
    """
    # Assign permission
    module_role = ModuleRole(
        user_id=user.id,
        module=module,
        role_name=role_name,
        granted_by=user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(user)

    # Create token with updated permissions
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(user)
    return {"Authorization": f"Bearer {access_token}"}

