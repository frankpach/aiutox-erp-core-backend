"""Configuration management router for module configurations."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.config.service import ConfigService
from app.core.db.deps import get_db
from app.core.exceptions import APIException, raise_bad_request, raise_not_found
from app.core.logging import get_client_info
from app.core.module_registry import get_module_registry
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.config import (
    ConfigUpdate,
    ModuleConfigResponse,
    ModuleInfoResponse,
    ModuleListItem,
)

router = APIRouter()


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
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key=f"modules.{module_id}.enabled",
        value=True,
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
    config_service.set(
        tenant_id=current_user.tenant_id,
        module="system",
        key=f"modules.{module_id}.enabled",
        value=False,
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
            tenant_id=current_user.tenant_id, module=module, config_dict=config_data
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



