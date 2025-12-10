"""Structured logging configuration for security and application events."""

import json
import logging
import sys
from typing import Any
from uuid import UUID

from app.core.config import get_settings

settings = get_settings()

# Create logger for security events
security_logger = logging.getLogger("app.security")
security_logger.setLevel(logging.INFO)

# Create logger for application events
app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

# Create console handler with structured format
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler.setFormatter(formatter)

# Add handler to loggers if not already added
if not security_logger.handlers:
    security_logger.addHandler(console_handler)
if not app_logger.handlers:
    app_logger.addHandler(console_handler)


def mask_email(email: str) -> str:
    """
    Mask email address for logging (show only first 3 chars and domain).

    Args:
        email: Email address to mask.

    Returns:
        Masked email string (e.g., "tes***@example.com").
    """
    if not email or "@" not in email:
        return "***"

    parts = email.split("@")
    local_part = parts[0]
    domain = parts[1]

    if len(local_part) <= 3:
        masked_local = "*" * len(local_part)
    else:
        masked_local = local_part[:3] + "***"

    return f"{masked_local}@{domain}"


def log_auth_success(user_id: str, email: str, tenant_id: str, ip_address: str | None = None) -> None:
    """
    Log successful authentication.

    Args:
        user_id: User UUID.
        email: User email (will be masked).
        tenant_id: Tenant UUID.
        ip_address: Client IP address (optional).
    """
    masked_email = mask_email(email)
    log_data: dict[str, Any] = {
        "event": "auth_success",
        "user_id": user_id,
        "email": masked_email,
        "tenant_id": tenant_id,
    }
    if ip_address:
        log_data["ip_address"] = ip_address

    security_logger.info(
        f"Authentication successful - user_id={user_id}, email={masked_email}, tenant_id={tenant_id}"
        + (f", ip={ip_address}" if ip_address else "")
    )


def log_auth_failure(
    email: str,
    reason: str,
    ip_address: str | None = None,
) -> None:
    """
    Log failed authentication attempt.

    Args:
        email: User email (will be masked).
        reason: Reason for failure (generic, doesn't reveal if user exists).
        ip_address: Client IP address (optional).
    """
    masked_email = mask_email(email)
    log_data: dict[str, Any] = {
        "event": "auth_failure",
        "email": masked_email,
        "reason": reason,
    }
    if ip_address:
        log_data["ip_address"] = ip_address

    security_logger.warning(
        f"Authentication failed - email={masked_email}, reason={reason}"
        + (f", ip={ip_address}" if ip_address else "")
    )


def log_rate_limit_exceeded(ip_address: str) -> None:
    """
    Log rate limit exceeded event.

    Args:
        ip_address: Client IP address.
    """
    security_logger.warning(f"Rate limit exceeded - ip={ip_address}")


def log_refresh_token_used(user_id: str, ip_address: str | None = None) -> None:
    """
    Log refresh token usage.

    Args:
        user_id: User UUID.
        ip_address: Client IP address (optional).
    """
    security_logger.info(
        f"Refresh token used - user_id={user_id}"
        + (f", ip={ip_address}" if ip_address else "")
    )


def log_refresh_token_invalid(reason: str, ip_address: str | None = None) -> None:
    """
    Log invalid refresh token attempt.

    Args:
        reason: Reason for invalidity.
        ip_address: Client IP address (optional).
    """
    security_logger.warning(
        f"Invalid refresh token - reason={reason}"
        + (f", ip={ip_address}" if ip_address else "")
    )


def log_logout(user_id: str, ip_address: str | None = None) -> None:
    """
    Log user logout.

    Args:
        user_id: User UUID.
        ip_address: Client IP address (optional).
    """
    security_logger.info(
        f"User logged out - user_id={user_id}"
        + (f", ip={ip_address}" if ip_address else "")
    )


def log_permission_change(
    user_id: str,
    action: str,
    target_user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log permission change event to console.

    Args:
        user_id: User who made the change.
        action: Action performed (grant, revoke, etc.).
        target_user_id: Target user ID (optional).
        details: Additional details (optional).
    """
    message = f"Permission change - user_id={user_id}, action={action}"
    if target_user_id:
        message += f", target_user_id={target_user_id}"
    if details:
        message += f", details={details}"

    security_logger.info(message)


def create_audit_log_entry(
    db: Any,
    user_id: UUID | None,
    tenant_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Create an audit log entry in the database.

    This function should be called after successful operations to persist
    audit information for compliance and security.

    Args:
        db: Database session.
        user_id: User who performed the action (None for system actions).
        tenant_id: Tenant ID for multi-tenancy.
        action: Action type (e.g., 'grant_permission', 'create_user').
        resource_type: Type of resource affected (e.g., 'user', 'permission').
        resource_id: ID of the resource affected.
        details: Additional details as JSON.
        ip_address: Client IP address.
        user_agent: Client user agent string.
    """
    if not settings.LOG_TO_DB:
        return

    try:
        from app.repositories.audit_repository import AuditRepository

        audit_repo = AuditRepository(db)
        audit_repo.create_audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        security_logger.error(f"Failed to create audit log entry: {e}")


def get_client_info(request: Any) -> tuple[str | None, str | None]:
    """
    Extract IP address and user agent from FastAPI request.

    Args:
        request: FastAPI Request object.

    Returns:
        Tuple of (ip_address, user_agent).
    """
    # Get IP address (check for proxy headers)
    ip_address = None
    if hasattr(request, "client") and request.client:
        ip_address = request.client.host

    # Check for forwarded IP (behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        ip_address = forwarded_for.split(",")[0].strip()

    # Get user agent
    user_agent = request.headers.get("User-Agent")

    return ip_address, user_agent


def log_user_action(
    action: str,
    user_id: str,
    target_user_id: str,
    tenant_id: str,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Log user management action to console.

    Args:
        action: Action type (e.g., 'create_user', 'update_user', 'deactivate_user').
        user_id: User who performed the action.
        target_user_id: Target user ID.
        tenant_id: Tenant ID.
        details: Additional details (optional).
        ip_address: Client IP address (optional).
        user_agent: Client user agent (optional).
    """
    message = f"User action - action={action}, user_id={user_id}, target_user_id={target_user_id}, tenant_id={tenant_id}"
    if details:
        message += f", details={details}"
    if ip_address:
        message += f", ip={ip_address}"

    security_logger.info(message)



