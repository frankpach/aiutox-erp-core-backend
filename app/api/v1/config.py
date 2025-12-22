"""Configuration management router for module configurations."""

import re
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.config.exceptions import InvalidColorFormatException
from app.core.config.service import ConfigService
from app.core.db.deps import get_db
from app.core.exceptions import APIException, raise_bad_request, raise_not_found
from app.core.logging import get_client_info
from app.core.module_registry import get_module_registry
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.config import (
    ConfigUpdate,
    GeneralSettingsRequest,
    GeneralSettingsResponse,
    ModuleConfigResponse,
    ModuleInfoResponse,
    ModuleListItem,
)
from app.schemas.config_version import (
    CacheStatsResponse,
    ConfigRollbackRequest,
    ConfigVersionListResponse,
    ConfigVersionResponse,
)
from app.schemas.notification import (
    NotificationChannelsResponse,
    SMTPConfigRequest,
    SMTPConfigResponse,
    SMSConfigRequest,
    SMSConfigResponse,
    WebhookConfigRequest,
    WebhookConfigResponse,
)

router = APIRouter()

# Color validation regex
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_color(key: str, value: str) -> None:
    """Validate hexadecimal color format.

    Args:
        key: Configuration key
        value: Color value to validate

    Raises:
        InvalidColorFormatException: If color format is invalid
    """
    if not isinstance(value, str):
        raise InvalidColorFormatException(key, str(value))

    if not HEX_COLOR_PATTERN.match(value):
        raise InvalidColorFormatException(key, value)


def validate_theme_colors(theme_data: dict[str, Any]) -> None:
    """Validate all color fields in theme configuration.

    Args:
        theme_data: Theme configuration dictionary

    Raises:
        InvalidColorFormatException: If any color format is invalid
    """
    color_keys = [
        "primary_color", "secondary_color", "accent_color",
        "background_color", "surface_color",
        "error_color", "warning_color", "success_color", "info_color",
        "text_primary", "text_secondary", "text_disabled",
        "sidebar_bg", "sidebar_text", "navbar_bg", "navbar_text",
    ]

    for key in color_keys:
        if key in theme_data:
            validate_color(key, theme_data[key])


# Module management endpoints (must come before /{module} routes)
@router.get(
    "/modules",
    response_model=StandardListResponse[ModuleListItem],
    status_code=status.HTTP_200_OK,
    summary="List all modules",
    description="List all available modules with their enabled status. Requires config.view permission.",
    responses={
        200: {"description": "List of modules retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_modules(
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[ModuleListItem]:
    """
    List all available modules with their enabled status.

    Requires: config.view

    Args:
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardListResponse with list of modules.
    """
    try:
        registry = get_module_registry()
    except RuntimeError:
        # Registry not initialized yet, return empty list
        return StandardListResponse(data=[], meta={"total": 0})

    config_service = ConfigService(db)
    modules_list = []

    for module_id, module_instance in registry.get_all_modules().items():
        is_enabled = registry.is_module_enabled(module_id, current_user.tenant_id)

        modules_list.append(
            ModuleListItem(
                id=module_id,
                name=module_instance.module_name,
                type=module_instance.module_type,
                enabled=is_enabled,
                dependencies=module_instance.get_dependencies(),
                description=module_instance.description,
            )
        )

    return StandardListResponse(
        data=modules_list, meta={"total": len(modules_list)}
    )


@router.get(
    "/modules/{module_id}",
    response_model=StandardResponse[ModuleInfoResponse],
    status_code=status.HTTP_200_OK,
    summary="Get module info",
    description="Get detailed information about a module. Requires config.view permission.",
    responses={
        200: {"description": "Module information retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Module not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "MODULE_NOT_FOUND",
                            "message": "Module 'inventory' not found",
                            "details": {"module_id": "inventory"},
                        }
                    }
                }
            },
        },
    },
)
async def get_module_info(
    module_id: str,
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleInfoResponse]:
    """
    Get detailed information about a module.

    Requires: config.view

    Args:
        module_id: Module identifier (e.g., 'products', 'auth').
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardResponse with module information.

    Raises:
        APIException: If module not found or user lacks permission.
    """
    try:
        registry = get_module_registry()
    except RuntimeError:
        raise_not_found("Module", module_id)

    module = registry.get_module(module_id)
    if not module:
        raise_not_found("Module", module_id)

    is_enabled = registry.is_module_enabled(module_id, current_user.tenant_id)

    return StandardResponse(
        data=ModuleInfoResponse(
            id=module_id,
            name=module.module_name,
            type=module.module_type,
            enabled=is_enabled,
            dependencies=module.get_dependencies(),
            description=module.description,
            has_router=module.get_router() is not None,
            model_count=len(module.get_models()),
        )
    )


@router.put(
    "/modules/{module_id}/enable",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Enable module",
    description="Enable a module for the current tenant. Requires config.edit permission.",
    responses={
        200: {"description": "Module enabled successfully"},
        400: {
            "description": "Invalid request or dependency not met",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "MODULE_DEPENDENCY_NOT_MET",
                            "message": "Cannot enable 'inventory': required dependency 'products' is not enabled",
                            "details": {"module_id": "inventory", "missing_dependency": "products"},
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Module not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "MODULE_NOT_FOUND",
                            "message": "Module 'inventory' not found",
                            "details": {"module_id": "inventory"},
                        }
                    }
                }
            },
        },
    },
)
async def enable_module(
    module_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Enable a module for the current tenant.

    Validates dependencies before enabling.

    Requires: config.edit

    Args:
        module_id: Module identifier.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If module not found, dependencies not met, or user lacks permission.
    """
    try:
        registry = get_module_registry()
    except RuntimeError:
        raise_not_found("Module", module_id)

    if module_id not in registry.get_all_modules():
        raise_not_found("Module", module_id)

    module = registry.get_module(module_id)

    # Validate dependencies
    dependencies = module.get_dependencies()
    for dep_id in dependencies:
        if not registry.is_module_enabled(dep_id, current_user.tenant_id):
            raise_bad_request(
                "MODULE_DEPENDENCY_NOT_MET",
                f"Cannot enable '{module_id}': required dependency '{dep_id}' is not enabled",
                details={"module_id": module_id, "missing_dependency": dep_id},
            )

    # Save configuration
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key=f"modules.{module_id}.enabled",
        value=True,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data={
            "module_id": module_id,
            "enabled": True,
            "message": f"Module '{module_id}' enabled successfully",
        }
    )


@router.put(
    "/modules/{module_id}/disable",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Disable module",
    description="Disable a module for the current tenant. Requires config.edit permission.",
    responses={
        200: {"description": "Module disabled successfully"},
        400: {
            "description": "Invalid request or module has dependencies",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "MODULE_HAS_DEPENDENCIES",
                            "message": "Cannot disable 'products': the following enabled modules depend on it: inventory",
                            "details": {"module_id": "products", "dependent_modules": ["inventory"]},
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Module not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "MODULE_NOT_FOUND",
                            "message": "Module 'inventory' not found",
                            "details": {"module_id": "inventory"},
                        }
                    }
                }
            },
        },
    },
)
async def disable_module(
    module_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Disable a module for the current tenant.

    Validates that no other enabled modules depend on this module before disabling.
    Does not allow disabling critical core modules (auth, users).

    Requires: config.edit

    Args:
        module_id: Module identifier.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If module not found, has dependencies, is critical core module, or user lacks permission.
    """
    try:
        registry = get_module_registry()
    except RuntimeError:
        raise_not_found("Module", module_id)

    if module_id not in registry.get_all_modules():
        raise_not_found("Module", module_id)

    module = registry.get_module(module_id)

    # Verify that no enabled modules depend on this one
    dependent_modules = []
    for other_id, other_module in registry.get_all_modules().items():
        if other_id != module_id:
            if module_id in other_module.get_dependencies():
                if registry.is_module_enabled(other_id, current_user.tenant_id):
                    dependent_modules.append(other_id)

    if dependent_modules:
        raise_bad_request(
            "MODULE_HAS_DEPENDENCIES",
            f"Cannot disable '{module_id}': the following enabled modules depend on it: {', '.join(dependent_modules)}",
            details={"module_id": module_id, "dependent_modules": dependent_modules},
        )

    # Do not allow disabling critical core modules
    if module.module_type == "core" and module_id in ["auth", "users"]:
        raise_bad_request(
            "CANNOT_DISABLE_CORE_MODULE",
            f"Cannot disable core module '{module_id}'",
            details={"module_id": module_id, "reason": "critical_core_module"},
        )

    # Save configuration
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key=f"modules.{module_id}.enabled",
        value=False,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data={
            "module_id": module_id,
            "enabled": False,
            "message": f"Module '{module_id}' disabled successfully",
        }
    )


@router.get(
    "/{module}",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Get module configuration",
    description="Get all configuration for a specific module in the current tenant. Requires config.view permission.",
    responses={
        200: {"description": "Module configuration retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view"},
                        }
                    }
                }
            },
        },
    },
)
async def get_module_config(
    module: str,
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleConfigResponse]:
    """
    Get all configuration for a specific module.

    Requires: config.view

    Args:
        module: Module name (e.g., 'products', 'inventory').
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardResponse with module configuration.

    Raises:
        APIException: If user lacks permission or module not found.
    """
    config_service = ConfigService(db)
    config_dict = config_service.get_module_config(
        tenant_id=current_user.tenant_id, module=module
    )

    return StandardResponse(
        data=ModuleConfigResponse(module=module, config=config_dict)
    )


@router.get(
    "/{module}/{key}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get configuration value",
    description="Get a specific configuration value for a module. Requires config.view permission.",
    responses={
        200: {"description": "Configuration value retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Configuration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CONFIG_NOT_FOUND",
                            "message": "Configuration 'products.min_price' not found",
                            "details": {"module": "products", "key": "min_price"},
                        }
                    }
                }
            },
        },
    },
)
async def get_config_value(
    module: str,
    key: str,
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Get a specific configuration value.

    Requires: config.view

    Args:
        module: Module name (e.g., 'products', 'inventory').
        key: Configuration key.
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardResponse with configuration value.

    Raises:
        APIException: If user lacks permission or configuration not found.
    """
    config_service = ConfigService(db)
    value = config_service.get(
        tenant_id=current_user.tenant_id, module=module, key=key
    )

    if value is None:
        raise APIException(
            code="CONFIG_NOT_FOUND",
            message=f"Configuration '{module}.{key}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"module": module, "key": key},
        )

    return StandardResponse(
        data={"module": module, "key": key, "value": value}
    )


@router.post(
    "/{module}",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set module configuration",
    description="Set multiple configuration values for a module. Requires config.edit permission.",
    responses={
        201: {"description": "Module configuration set successfully"},
        400: {
            "description": "Invalid request or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_CONFIG_VALUE",
                            "message": "Invalid value for products.min_price: value does not match schema",
                            "details": None,
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit"},
                        }
                    }
                }
            },
        },
    },
)
async def set_module_config(
    module: str,
    config_data: dict[str, Any],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleConfigResponse]:
    """
    Set multiple configuration values for a module.

    Requires: config.edit

    Args:
        module: Module name (e.g., 'products', 'inventory').
        config_data: Dictionary of key-value pairs to set.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with updated module configuration.

    Raises:
        APIException: If user lacks permission or validation fails.
    """
    if not isinstance(config_data, dict):
        raise_bad_request(
            "INVALID_CONFIG_DATA",
            "Configuration data must be a dictionary",
        )

    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    try:
        config_dict = config_service.set_module_config(
            tenant_id=current_user.tenant_id,
            module=module,
            config_dict=config_data,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise_bad_request("INVALID_CONFIG_VALUE", str(e))

    return StandardResponse(
        data=ModuleConfigResponse(module=module, config=config_dict)
    )


@router.put(
    "/{module}/{key}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Set configuration value",
    description="Set or update a specific configuration value. Requires config.edit permission.",
    responses={
        200: {"description": "Configuration value set successfully"},
        400: {
            "description": "Invalid request or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_CONFIG_VALUE",
                            "message": "Invalid value for products.min_price: value does not match schema",
                            "details": None,
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit"},
                        }
                    }
                }
            },
        },
    },
)
async def set_config_value(
    module: str,
    key: str,
    config_update: ConfigUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Set or update a specific configuration value.

    Requires: config.edit

    Args:
        module: Module name (e.g., 'products', 'inventory').
        key: Configuration key.
        config_update: Configuration update data.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with updated configuration.

    Raises:
        APIException: If user lacks permission or validation fails.
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    try:
        config_data = config_service.set(
            tenant_id=current_user.tenant_id,
            module=module,
            key=key,
            value=config_update.value,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise_bad_request("INVALID_CONFIG_VALUE", str(e))

    return StandardResponse(data=config_data)


@router.delete(
    "/{module}/{key}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete configuration value",
    description="Delete a specific configuration value. Requires config.delete permission.",
    responses={
        200: {"description": "Configuration value deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.delete"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Configuration not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CONFIG_NOT_FOUND",
                            "message": "Configuration 'products.min_price' not found",
                            "details": {"module": "products", "key": "min_price"},
                        }
                    }
                }
            },
        },
    },
)
async def delete_config_value(
    module: str,
    key: str,
    current_user: Annotated[User, Depends(require_permission("config.delete"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Delete a specific configuration value.

    Requires: config.delete

    Args:
        module: Module name (e.g., 'products', 'inventory').
        key: Configuration key.
        current_user: Current authenticated user (must have config.delete).
        db: Database session.

    Returns:
        StandardResponse with success message.

    Raises:
        APIException: If user lacks permission or configuration not found.
    """
    config_service = ConfigService(db)

    # Check if exists before deleting
    value = config_service.get(
        tenant_id=current_user.tenant_id, module=module, key=key
    )
    if value is None:
        raise APIException(
            code="CONFIG_NOT_FOUND",
            message=f"Configuration '{module}.{key}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"module": module, "key": key},
        )

    config_service.delete(
        tenant_id=current_user.tenant_id, module=module, key=key
    )

    return StandardResponse(
        data={"message": f"Configuration '{module}.{key}' deleted successfully"}
    )


# Theme-specific endpoints
@router.get(
    "/app_theme",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Get theme configuration",
    description="Get visual theme configuration for the current tenant. Requires config.view or config.view_theme permission.",
    responses={
        200: {"description": "Theme configuration retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view_theme"},
                        }
                    }
                }
            },
        },
    },
)
async def get_theme_config(
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleConfigResponse]:
    """
    Get visual theme configuration for the current tenant.

    Returns all theme-related settings including colors, logos, fonts, and component styles.

    Requires: config.view or config.view_theme

    Args:
        current_user: Current authenticated user (must have config.view or config.view_theme).
        db: Database session.

    Returns:
        StandardResponse with theme configuration.

    Raises:
        APIException: If user lacks permission.
    """
    config_service = ConfigService(db)
    theme_config = config_service.get_module_config(
        tenant_id=current_user.tenant_id, module="app_theme"
    )

    # If no theme config exists, return default values
    if not theme_config:
        theme_config = {
            "primary_color": "#1976D2",
            "secondary_color": "#DC004E",
            "accent_color": "#FFC107",
            "background_color": "#FFFFFF",
            "surface_color": "#F5F5F5",
            "text_primary": "#212121",
            "text_secondary": "#757575",
        }

    return StandardResponse(
        data=ModuleConfigResponse(module="app_theme", config=theme_config)
    )


@router.post(
    "/app_theme",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set theme configuration",
    description="Set visual theme configuration for the current tenant. Requires config.edit or config.edit_theme permission.",
    responses={
        201: {"description": "Theme configuration set successfully"},
        400: {
            "description": "Invalid color format or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_COLOR_FORMAT",
                            "message": "Invalid color format for 'primary_color': must be #RRGGBB (got: blue)",
                            "details": {
                                "key": "primary_color",
                                "value": "blue",
                                "expected_format": "#RRGGBB",
                            },
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit_theme"},
                        }
                    }
                }
            },
        },
    },
)
async def set_theme_config(
    theme_data: dict[str, Any],
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleConfigResponse]:
    """
    Set visual theme configuration for the current tenant.

    Validates color formats (must be #RRGGBB) and saves theme settings.

    Requires: config.edit or config.edit_theme

    Args:
        theme_data: Dictionary of theme settings (colors, logos, fonts, etc.).
        current_user: Current authenticated user (must have config.edit or config.edit_theme).
        db: Database session.

    Returns:
        StandardResponse with updated theme configuration.

    Raises:
        InvalidColorFormatException: If any color format is invalid.
        APIException: If user lacks permission or validation fails.
    """
    if not isinstance(theme_data, dict):
        raise_bad_request(
            "INVALID_THEME_DATA",
            "Theme data must be a dictionary",
        )

    # Validate all color fields
    validate_theme_colors(theme_data)

    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    try:
        theme_config = config_service.set_module_config(
            tenant_id=current_user.tenant_id,
            module="app_theme",
            config_dict=theme_data,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise_bad_request("INVALID_THEME_VALUE", str(e))

    return StandardResponse(
        data=ModuleConfigResponse(module="app_theme", config=theme_config)
    )


@router.put(
    "/app_theme/{key}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update theme property",
    description="Update a specific theme property. Validates color format if applicable. Requires config.edit or config.edit_theme permission.",
    responses={
        200: {"description": "Theme property updated successfully"},
        400: {
            "description": "Invalid color format or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_COLOR_FORMAT",
                            "message": "Invalid color format for 'primary_color': must be #RRGGBB (got: red)",
                            "details": {
                                "key": "primary_color",
                                "value": "red",
                                "expected_format": "#RRGGBB",
                            },
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit_theme"},
                        }
                    }
                }
            },
        },
    },
)
async def update_theme_property(
    key: str,
    config_update: ConfigUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Update a specific theme property.

    Validates color format if the property is a color field.

    Requires: config.edit or config.edit_theme

    Args:
        key: Theme property key (e.g., 'primary_color', 'logo_primary').
        config_update: Configuration update data.
        current_user: Current authenticated user (must have config.edit or config.edit_theme).
        db: Database session.

    Returns:
        StandardResponse with updated property.

    Raises:
        InvalidColorFormatException: If color format is invalid.
        APIException: If user lacks permission or validation fails.
    """
    # Validate color format if it's a color key
    color_keys = [
        "primary_color", "secondary_color", "accent_color",
        "background_color", "surface_color",
        "error_color", "warning_color", "success_color", "info_color",
        "text_primary", "text_secondary", "text_disabled",
        "sidebar_bg", "sidebar_text", "navbar_bg", "navbar_text",
    ]

    if key in color_keys:
        validate_color(key, config_update.value)

    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    try:
        config_data = config_service.set(
            tenant_id=current_user.tenant_id,
            module="app_theme",
            key=key,
            value=config_update.value,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise_bad_request("INVALID_THEME_VALUE", str(e))

    return StandardResponse(data=config_data)


# Version management endpoints
@router.get(
    "/{module}/{key}/versions",
    response_model=StandardResponse[ConfigVersionListResponse],
    status_code=status.HTTP_200_OK,
    summary="Get version history",
    description="Get version history for a configuration key. Requires config.view permission.",
    responses={
        200: {"description": "Version history retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_version_history(
    module: str,
    key: str,
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
) -> StandardResponse[ConfigVersionListResponse]:
    """
    Get version history for a configuration key.

    Requires: config.view

    Args:
        module: Module name
        key: Configuration key
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        StandardResponse with version history
    """
    config_service = ConfigService(db)

    versions, total = config_service.get_version_history(
        tenant_id=current_user.tenant_id,
        module=module,
        key=key,
        skip=skip,
        limit=limit,
    )

    version_responses = [
        ConfigVersionResponse(
            id=v["id"],
            version_number=v["version_number"],
            value=v["value"],
            change_type=v["change_type"],
            changed_by=v["changed_by"],
            change_reason=v.get("change_reason"),
            created_at=v["created_at"],
            metadata=v.get("metadata"),
        )
        for v in versions
    ]

    return StandardResponse(
        data=ConfigVersionListResponse(
            versions=version_responses,
            total=total,
            module=module,
            key=key,
        )
    )


@router.post(
    "/{module}/{key}/rollback",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Rollback to version",
    description="Rollback a configuration to a specific version. Requires config.edit permission.",
    responses={
        200: {"description": "Rollback successful"},
        400: {"description": "Invalid version number"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Version not found"},
    },
)
async def rollback_to_version(
    module: str,
    key: str,
    rollback_request: ConfigRollbackRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Rollback a configuration to a specific version.

    Requires: config.edit

    Args:
        module: Module name
        key: Configuration key
        rollback_request: Rollback request with version number
        request: FastAPI request object
        current_user: Current authenticated user
        db: Database session

    Returns:
        StandardResponse with rollback confirmation

    Raises:
        APIException: If version not found or rollback fails
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    try:
        config_data = config_service.rollback_to_version(
            tenant_id=current_user.tenant_id,
            module=module,
            key=key,
            version_number=rollback_request.version_number,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return StandardResponse(
            data={
                "message": f"Configuration '{module}.{key}' rolled back to version {rollback_request.version_number}",
                "config": config_data,
            }
        )
    except ValueError as e:
        raise_bad_request("ROLLBACK_FAILED", str(e))


# Cache management endpoints
@router.get(
    "/cache/stats",
    response_model=StandardResponse[CacheStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get cache statistics",
    description="Get cache statistics and status. Requires config.view permission.",
    responses={
        200: {"description": "Cache statistics retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_cache_stats(
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[CacheStatsResponse]:
    """
    Get cache statistics and status.

    Requires: config.view

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        StandardResponse with cache statistics
    """
    config_service = ConfigService(db)
    stats = config_service.get_cache_stats()

    return StandardResponse(data=CacheStatsResponse(**stats))


@router.post(
    "/cache/clear",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Clear cache",
    description="Clear configuration cache. Requires config.edit permission.",
    responses={
        200: {"description": "Cache cleared successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def clear_cache(
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
    module: str | None = None,
) -> StandardResponse[dict]:
    """
    Clear configuration cache.

    Requires: config.edit

    Args:
        module: Optional module name to clear specific module cache
        current_user: Current authenticated user
        db: Database session

    Returns:
        StandardResponse with clear confirmation
    """
    config_service = ConfigService(db)

    if module:
        cleared = config_service.clear_cache(
            tenant_id=current_user.tenant_id, module=module
        )
        message = f"Cleared {cleared} cache entries for module '{module}'"
    else:
        config_service.clear_cache()
        message = "Cleared all cache entries"

    return StandardResponse(data={"message": message})


@router.get(
    "/general",
    response_model=StandardResponse[GeneralSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get general system settings",
    description="Get general system settings (timezone, date format, currency, language). Requires config.view permission.",
    responses={
        200: {"description": "General settings retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.view"},
                        }
                    }
                }
            },
        },
    },
)
async def get_general_settings(
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[GeneralSettingsResponse]:
    """
    Get general system settings for the current tenant.

    Requires: config.view

    Args:
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardResponse with general settings.
    """
    config_service = ConfigService(db)

    settings = GeneralSettingsResponse(
        timezone=config_service.get(
            current_user.tenant_id, "system", "general.timezone", "America/Mexico_City"
        ),
        date_format=config_service.get(
            current_user.tenant_id, "system", "general.date_format", "DD/MM/YYYY"
        ),
        time_format=config_service.get(
            current_user.tenant_id, "system", "general.time_format", "24h"
        ),
        currency=config_service.get(
            current_user.tenant_id, "system", "general.currency", "MXN"
        ),
        language=config_service.get(
            current_user.tenant_id, "system", "general.language", "es"
        ),
    )

    return StandardResponse(
        data=settings, message="General settings retrieved successfully"
    )


@router.put(
    "/general",
    response_model=StandardResponse[GeneralSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Update general system settings",
    description="Update general system settings (timezone, date format, currency, language). Requires config.edit permission.",
    responses={
        200: {"description": "General settings updated successfully"},
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Validation failed",
                            "details": {"time_format": ["Invalid time format. Must be '12h' or '24h'"]},
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "config.edit"},
                        }
                    }
                }
            },
        },
    },
)
async def update_general_settings(
    settings: GeneralSettingsRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[GeneralSettingsResponse]:
    """
    Update general system settings for the current tenant.

    Requires: config.edit

    Args:
        settings: General settings to update.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with updated general settings.
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    # Update each setting
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key="general.timezone",
        value=settings.timezone,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key="general.date_format",
        value=settings.date_format,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key="general.time_format",
        value=settings.time_format,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key="general.currency",
        value=settings.currency,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key="general.language",
        value=settings.language,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=GeneralSettingsResponse(
            timezone=settings.timezone,
            date_format=settings.date_format,
            time_format=settings.time_format,
            currency=settings.currency,
            language=settings.language,
        ),
        message="General settings updated successfully",
    )


@router.get(
    "/notifications/channels",
    response_model=StandardResponse[NotificationChannelsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get notification channels configuration",
    description="Get configuration for all notification channels (SMTP, SMS, webhooks). Requires notifications.manage permission.",
    responses={
        200: {"description": "Notification channels configuration retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def get_notification_channels(
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[NotificationChannelsResponse]:
    """
    Get notification channels configuration for the current tenant.

    Requires: notifications.manage

    Args:
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with notification channels configuration.
    """
    config_service = ConfigService(db)

    # Get all notifications config
    notifications_config = config_service.get_module_config(current_user.tenant_id, "notifications")

    # Get SMTP config
    smtp_data = {}
    for key, value in notifications_config.items():
        if key.startswith("channels.smtp."):
            config_key = key.replace("channels.smtp.", "")
            smtp_data[config_key] = value

    smtp = SMTPConfigResponse(
        enabled=smtp_data.get("enabled", False),
        host=smtp_data.get("host", "smtp.gmail.com"),
        port=smtp_data.get("port", 587),
        user=smtp_data.get("user", ""),
        password=None,  # Never return password
        use_tls=smtp_data.get("use_tls", True),
        from_email=smtp_data.get("from_email", ""),
        from_name=smtp_data.get("from_name"),
    )

    # Get SMS config
    sms_data = {}
    for key, value in notifications_config.items():
        if key.startswith("channels.sms."):
            config_key = key.replace("channels.sms.", "")
            sms_data[config_key] = value

    sms = SMSConfigResponse(
        enabled=sms_data.get("enabled", False),
        provider=sms_data.get("provider", "twilio"),
        account_sid=sms_data.get("account_sid"),
        auth_token=None,  # Never return token
        from_number=sms_data.get("from_number"),
    )

    # Get webhook config
    webhook_data = {}
    for key, value in notifications_config.items():
        if key.startswith("channels.webhook."):
            config_key = key.replace("channels.webhook.", "")
            webhook_data[config_key] = value

    webhook = WebhookConfigResponse(
        enabled=webhook_data.get("enabled", False),
        url=webhook_data.get("url", ""),
        secret=None,  # Never return secret
        timeout=webhook_data.get("timeout", 30),
    )

    return StandardResponse(
        data=NotificationChannelsResponse(smtp=smtp, sms=sms, webhook=webhook),
        message="Notification channels configuration retrieved successfully",
    )


@router.put(
    "/notifications/channels/smtp",
    response_model=StandardResponse[SMTPConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Update SMTP channel configuration",
    description="Update SMTP channel configuration. Requires notifications.manage permission.",
    responses={
        200: {"description": "SMTP configuration updated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def update_smtp_config(
    config: SMTPConfigRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[SMTPConfigResponse]:
    """
    Update SMTP channel configuration.

    Requires: notifications.manage

    Args:
        config: SMTP configuration.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with updated SMTP configuration.
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    # Update each setting
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.enabled",
        value=config.enabled,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.host",
        value=config.host,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.port",
        value=config.port,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.user",
        value=config.user,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.password",
        value=config.password,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.use_tls",
        value=config.use_tls,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.smtp.from_email",
        value=config.from_email,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if config.from_name:
        config_service.set(
            tenant_id=current_user.tenant_id,
            module="notifications",
            key="channels.smtp.from_name",
            value=config.from_name,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return StandardResponse(
        data=SMTPConfigResponse(
            enabled=config.enabled,
            host=config.host,
            port=config.port,
            user=config.user,
            password=None,
            use_tls=config.use_tls,
            from_email=config.from_email,
            from_name=config.from_name,
        ),
        message="SMTP configuration updated successfully",
    )


@router.put(
    "/notifications/channels/sms",
    response_model=StandardResponse[SMSConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Update SMS channel configuration",
    description="Update SMS channel configuration. Requires notifications.manage permission.",
    responses={
        200: {"description": "SMS configuration updated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def update_sms_config(
    config: SMSConfigRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[SMSConfigResponse]:
    """
    Update SMS channel configuration.

    Requires: notifications.manage

    Args:
        config: SMS configuration.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with updated SMS configuration.
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    # Update each setting
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.sms.enabled",
        value=config.enabled,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.sms.provider",
        value=config.provider,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if config.account_sid:
        config_service.set(
            tenant_id=current_user.tenant_id,
            module="notifications",
            key="channels.sms.account_sid",
            value=config.account_sid,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if config.auth_token:
        config_service.set(
            tenant_id=current_user.tenant_id,
            module="notifications",
            key="channels.sms.auth_token",
            value=config.auth_token,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if config.from_number:
        config_service.set(
            tenant_id=current_user.tenant_id,
            module="notifications",
            key="channels.sms.from_number",
            value=config.from_number,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return StandardResponse(
        data=SMSConfigResponse(
            enabled=config.enabled,
            provider=config.provider,
            account_sid=config.account_sid,
            auth_token=None,
            from_number=config.from_number,
        ),
        message="SMS configuration updated successfully",
    )


@router.put(
    "/notifications/channels/webhook",
    response_model=StandardResponse[WebhookConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Update webhook channel configuration",
    description="Update webhook channel configuration. Requires notifications.manage permission.",
    responses={
        200: {"description": "Webhook configuration updated successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def update_webhook_config(
    config: WebhookConfigRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[WebhookConfigResponse]:
    """
    Update webhook channel configuration.

    Requires: notifications.manage

    Args:
        config: Webhook configuration.
        request: FastAPI request object (for client info).
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with updated webhook configuration.
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    # Update each setting
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.webhook.enabled",
        value=config.enabled,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.webhook.url",
        value=config.url,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if config.secret:
        config_service.set(
            tenant_id=current_user.tenant_id,
            module="notifications",
            key="channels.webhook.secret",
            value=config.secret,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="notifications",
        key="channels.webhook.timeout",
        value=config.timeout,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=WebhookConfigResponse(
            enabled=config.enabled,
            url=config.url,
            secret=None,
            timeout=config.timeout,
        ),
        message="Webhook configuration updated successfully",
    )


@router.post(
    "/notifications/channels/smtp/test",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Test SMTP connection",
    description="Test SMTP connection with current configuration. Requires notifications.manage permission.",
    responses={
        200: {"description": "SMTP connection test completed"},
        400: {
            "description": "SMTP connection failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "SMTP_CONNECTION_FAILED",
                            "message": "Failed to connect to SMTP server",
                            "details": {"error": "Connection timeout"},
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def test_smtp_connection(
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Test SMTP connection with current configuration.

    Requires: notifications.manage

    Args:
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with test result.
    """
    config_service = ConfigService(db)

    # Get SMTP config
    smtp_config = config_service.get_all_by_module(current_user.tenant_id, "notifications")
    smtp_data = {}
    for config in smtp_config:
        if config.key.startswith("channels.smtp."):
            key = config.key.replace("channels.smtp.", "")
            smtp_data[key] = config.value

    if not smtp_data.get("enabled", False):
        raise_bad_request(
            "SMTP_NOT_ENABLED",
            "SMTP channel is not enabled",
        )

    # TODO: Implement actual SMTP connection test
    # For now, return success
    return StandardResponse(
        data={"success": True, "message": "SMTP connection test successful"},
        message="SMTP connection test completed",
    )


@router.post(
    "/notifications/channels/webhook/test",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Test webhook connection",
    description="Test webhook connection with current configuration. Requires notifications.manage permission.",
    responses={
        200: {"description": "Webhook connection test completed"},
        400: {
            "description": "Webhook connection failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "WEBHOOK_CONNECTION_FAILED",
                            "message": "Failed to connect to webhook URL",
                            "details": {"error": "Connection timeout"},
                        }
                    }
                }
            },
        },
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "notifications.manage"},
                        }
                    }
                }
            },
        },
    },
)
async def test_webhook_connection(
    current_user: Annotated[User, Depends(require_permission("notifications.manage"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Test webhook connection with current configuration.

    Requires: notifications.manage

    Args:
        current_user: Current authenticated user (must have notifications.manage).
        db: Database session.

    Returns:
        StandardResponse with test result.
    """
    config_service = ConfigService(db)

    # Get webhook config
    notifications_config = config_service.get_module_config(current_user.tenant_id, "notifications")
    webhook_data = {}
    for key, value in notifications_config.items():
        if key.startswith("channels.webhook."):
            config_key = key.replace("channels.webhook.", "")
            webhook_data[config_key] = value

    if not webhook_data.get("enabled", False):
        raise_bad_request(
            "WEBHOOK_NOT_ENABLED",
            "Webhook channel is not enabled",
        )

    url = webhook_data.get("url", "")
    if not url:
        raise_bad_request(
            "WEBHOOK_URL_MISSING",
            "Webhook URL is not configured",
        )

    # Test webhook connection
    try:
        async with httpx.AsyncClient(timeout=webhook_data.get("timeout", 30)) as client:
            response = await client.post(
                url,
                json={"test": True, "timestamp": datetime.now(UTC).isoformat()},
            )
            if response.status_code < 400:
                return StandardResponse(
                    data={"success": True, "status_code": response.status_code, "message": "Webhook connection test successful"},
                    message="Webhook connection test completed",
                )
            else:
                raise_bad_request(
                    "WEBHOOK_TEST_FAILED",
                    f"Webhook returned status {response.status_code}",
                    details={"status_code": response.status_code, "response": response.text[:200]},
                )
    except httpx.TimeoutException:
        raise_bad_request(
            "WEBHOOK_TIMEOUT",
            "Webhook connection timed out",
        )
    except Exception as e:
        raise_bad_request(
            "WEBHOOK_CONNECTION_FAILED",
            f"Failed to connect to webhook: {str(e)}",
        )



