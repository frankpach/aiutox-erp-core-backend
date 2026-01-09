"""Configuration management router for module configurations."""

import re
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, Request, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.config.exceptions import InvalidColorFormatException
from app.core.config.service import ConfigService
from app.core.config.theme_preset_service import ThemePresetService
from app.core.db.deps import get_db
from app.core.exceptions import APIException, raise_bad_request, raise_not_found
from app.core.logging import get_client_info
from app.core.module_registry import get_module_registry
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.config import (
    ConfigCreate,
    ConfigResponse,
    ConfigUpdate,
    GeneralSettingsRequest,
    GeneralSettingsResponse,
    ModuleConfigResponse,
    ModuleInfoResponse,
    ModuleListItem,
    ThemePresetCreate,
    ThemePresetResponse,
    ThemePresetUpdate,
)
from app.schemas.file_config import (
    StorageConfigResponse,
    StorageConfigUpdate,
    StorageStatsResponse,
    FileLimitsResponse,
    FileLimitsUpdate,
    ThumbnailConfigResponse,
    ThumbnailConfigUpdate,
    S3ConnectionTestRequest,
    S3ConnectionTestResponse,
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

    for key, value in theme_data.items():
        if key in color_keys:
            validate_color(key, value)
            continue

        if isinstance(key, str) and key.startswith("dark_"):
            base_key = key.replace("dark_", "", 1)
            if base_key in color_keys:
                validate_color(key, value)


# Module management endpoints (must come before /{module} routes)
@router.get(
    "/modules",
    response_model=StandardListResponse[ModuleListItem],
    status_code=status.HTTP_200_OK,
    summary="List all modules",
    description="List all available modules with their enabled status. Requires config.view permission.",
    response_model_exclude_none=True,
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
    import json
    import traceback

    try:
        registry = get_module_registry()
    except RuntimeError:
        # Registry not initialized yet, return empty list
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Registry not initialized, returning empty list", "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "R"}) + "\n")
        except: pass

        return StandardListResponse(
            data=[],
            meta=PaginationMeta(
                total=0,
                page=1,
                page_size=1,  # Must be >= 1 per PaginationMeta validation
                total_pages=0,
            ),
        )
    except Exception as e:
        # Log unexpected errors
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Error getting registry", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "E"}) + "\n")
        except: pass
        raise

    try:
        config_service = ConfigService(db)
        modules_list = []

        for module_id, module_instance in registry.get_all_modules().items():
            try:
                is_enabled = registry.is_module_enabled(module_id, current_user.tenant_id)

                # Ensure all fields are valid and have correct types
                module_name = getattr(module_instance, "module_name", "") or ""
                module_type = getattr(module_instance, "module_type", "business") or "business"
                dependencies = getattr(module_instance, "get_dependencies", lambda: [])() or []
                description = getattr(module_instance, "description", "") or ""

                # Ensure dependencies is a list of strings
                if not isinstance(dependencies, list):
                    dependencies = []
                dependencies = [str(dep) for dep in dependencies if dep]

                modules_list.append(
                    ModuleListItem(
                        id=str(module_id),
                        name=str(module_name),
                        type=str(module_type),
                        enabled=bool(is_enabled),
                        dependencies=dependencies,
                        description=str(description),
                    )
                )
            except Exception as module_error:
                # Log error for individual module but continue
                try:
                    with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                        log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Error processing module", "data": {"module_id": module_id, "error": str(module_error), "error_type": type(module_error).__name__, "traceback": traceback.format_exc()}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "M"}) + "\n")
                except: pass
                continue

        # Create response with proper error handling
        try:
            pagination_meta = PaginationMeta(
                total=len(modules_list),
                page=1,
                page_size=len(modules_list) if modules_list else 1,
                total_pages=1,
            )

            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                    log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Creating PaginationMeta", "data": {"total": len(modules_list), "page": 1, "page_size": len(modules_list) if modules_list else 1, "total_pages": 1}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "PM"}) + "\n")
            except: pass

            # Validate response before returning
            try:
                response = StandardListResponse(
                    data=modules_list,
                    meta=pagination_meta,
                )

                # Try to serialize to catch any validation errors
                try:
                    response.model_dump_json()
                except Exception as serialization_error:
                    try:
                        with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                            log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Serialization error", "data": {"error": str(serialization_error), "error_type": type(serialization_error).__name__, "traceback": traceback.format_exc()}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "SE"}) + "\n")
                    except: pass
                    raise

                try:
                    with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                        log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Response created successfully", "data": {"modules_count": len(modules_list)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "S"}) + "\n")
                except: pass

                return response
            except Exception as response_creation_error:
                # Log error creating response
                try:
                    with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                        log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Error creating StandardListResponse", "data": {"error": str(response_creation_error), "error_type": type(response_creation_error).__name__, "traceback": traceback.format_exc(), "modules_count": len(modules_list)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "RE"}) + "\n")
                except: pass
                raise
        except Exception as response_error:
            # Log error creating response
            try:
                with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                    log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Error creating StandardListResponse", "data": {"error": str(response_error), "error_type": type(response_error).__name__, "traceback": traceback.format_exc(), "modules_count": len(modules_list)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "RE"}) + "\n")
            except: pass
            raise
    except Exception as e:
        # Log error creating response
        try:
            with open(r"d:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\.cursor\debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps({"location": "config.py:list_modules", "message": "Error creating response", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "RE"}) + "\n")
        except: pass
        raise


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


# Theme-specific endpoints (must be before generic /{module} routes)
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
    """
    config_service = ConfigService(db)
    theme_config = config_service.get_module_config(
        tenant_id=current_user.tenant_id, module="app_theme"
    )

    # If no theme config exists, return default values
    # get_module_config returns {} when empty, which is falsy
    if not theme_config:
        theme_config = {
            "primary_color": "#023E87",
            "secondary_color": "#F1F5F9",
            "accent_color": "#F1F5F9",
            "background_color": "#FFFFFF",
            "surface_color": "#FFFFFF",
            "error_color": "#EF4444",
            "warning_color": "#F59E0B",
            "success_color": "#10B981",
            "info_color": "#3B82F6",
            "text_primary": "#0F172A",
            "text_secondary": "#64748B",
            "text_disabled": "#94A3B8",
            "sidebar_bg": "#FAFAFA",
            "sidebar_text": "#0F172A",
            "navbar_bg": "#FFFFFF",
            "navbar_text": "#0F172A",
        }

    return StandardResponse(
        data=ModuleConfigResponse(module="app_theme", config=theme_config)
    )


# Cache management endpoints (must come before /{module} routes)
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
        current_user: Current authenticated user
        db: Database session
        module: Optional module name to clear cache for specific module

    Returns:
        StandardResponse with success message
    """
    config_service = ConfigService(db)
    config_service.clear_cache()

    if module:
        message = f"Cache cleared for module '{module}'"
    else:
        message = "Cache cleared successfully"

    return StandardResponse(data={"message": message})


# Theme-specific endpoints (must be before generic /{module} routes)
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
    theme_data: Annotated[dict[str, Any], Body()],
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
    try:
        validate_theme_colors(theme_data)
    except InvalidColorFormatException as e:
        # Re-raise to ensure FastAPI exception handler handles it correctly
        raise e

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


# Generic module configuration endpoints (must come after specific routes)
@router.post(
    "/{module}",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Set module configuration",
    description="Set multiple configuration values for a module. Requires config.edit permission.",
    responses={
        201: {"description": "Module configuration set successfully"},
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
        module: Module name
        config_data: Configuration data as key-value pairs
        request: FastAPI request object
        current_user: Current authenticated user (must have config.edit)
        db: Database session

    Returns:
        StandardResponse with module configuration
    """
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)

    # Set each configuration value
    for key, value in config_data.items():
        config_service.set(
            tenant_id=current_user.tenant_id,
            module=module,
            key=key,
            value=value,
            user_id=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return StandardResponse(
        data=ModuleConfigResponse(module=module, config=config_data),
        message=f"Module '{module}' configuration set successfully",
    )


# Theme preset endpoints (must come before /{module} routes)
@router.get(
    "/app_theme/presets",
    response_model=StandardListResponse[ThemePresetResponse],
    status_code=status.HTTP_200_OK,
    summary="List theme presets",
    description="List all theme presets for the current tenant. Requires config.view permission.",
    responses={
        200: {"description": "Theme presets retrieved successfully"},
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
async def list_theme_presets(
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[ThemePresetResponse]:
    """
    List all theme presets for the current tenant.

    Requires: config.view

    Args:
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardListResponse with list of theme presets.
    """
    preset_service = ThemePresetService(db)
    presets = preset_service.list_presets(current_user.tenant_id)

    return StandardListResponse(
        data=[ThemePresetResponse.model_validate(preset) for preset in presets],
        meta=PaginationMeta(
            total=len(presets),
            page=1,
            page_size=len(presets) if presets else 1,  # Must be >= 1 per PaginationMeta validation
            total_pages=1,
        ),
    )


@router.post(
    "/app_theme/presets",
    response_model=StandardResponse[ThemePresetResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create theme preset",
    description="Create a new theme preset. Requires config.edit permission.",
    responses={
        201: {"description": "Theme preset created successfully"},
        400: {
            "description": "Invalid request or validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRESET_NAME_EXISTS",
                            "message": "Preset with name 'My Theme' already exists",
                            "details": {"name": "My Theme"},
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
async def create_theme_preset(
    preset_data: ThemePresetCreate,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ThemePresetResponse]:
    """
    Create a new theme preset.

    Requires: config.edit

    Args:
        preset_data: Preset creation data.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with created theme preset.
    """
    # Validate theme colors if config is provided
    if preset_data.config:
        validate_theme_colors(preset_data.config)

    preset_service = ThemePresetService(db)
    preset = preset_service.create_preset(
        tenant_id=current_user.tenant_id,
        name=preset_data.name,
        config=preset_data.config,
        description=preset_data.description,
        is_default=preset_data.is_default,
        created_by=current_user.id,
    )

    return StandardResponse(
        data=ThemePresetResponse.model_validate(preset),
        message="Theme preset created successfully",
    )


@router.get(
    "/app_theme/presets/{preset_id}",
    response_model=StandardResponse[ThemePresetResponse],
    status_code=status.HTTP_200_OK,
    summary="Get theme preset",
    description="Get a specific theme preset. Requires config.view permission.",
    responses={
        200: {"description": "Theme preset retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Theme preset not found"},
    },
)
async def get_theme_preset(
    preset_id: UUID,
    current_user: Annotated[User, Depends(require_permission("config.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ThemePresetResponse]:
    """
    Get a specific theme preset.

    Requires: config.view

    Args:
        preset_id: Preset ID.
        current_user: Current authenticated user (must have config.view).
        db: Database session.

    Returns:
        StandardResponse with theme preset.
    """
    preset_service = ThemePresetService(db)
    preset = preset_service.get_preset(preset_id, current_user.tenant_id)

    return StandardResponse(data=ThemePresetResponse.model_validate(preset))


@router.put(
    "/app_theme/presets/{preset_id}",
    response_model=StandardResponse[ThemePresetResponse],
    status_code=status.HTTP_200_OK,
    summary="Update theme preset",
    description="Update a theme preset. System presets cannot be updated. Requires config.edit permission.",
    responses={
        200: {"description": "Theme preset updated successfully"},
        400: {
            "description": "Invalid request or cannot edit system preset",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CANNOT_EDIT_SYSTEM_PRESET",
                            "message": "System presets cannot be edited",
                            "details": {"preset_id": "...", "preset_name": "Original"},
                        }
                    }
                }
            },
        },
        403: {"description": "Insufficient permissions"},
        404: {"description": "Theme preset not found"},
    },
)
async def update_theme_preset(
    preset_id: UUID,
    preset_data: ThemePresetUpdate,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ThemePresetResponse]:
    """
    Update a theme preset.

    System presets cannot be updated.

    Requires: config.edit

    Args:
        preset_id: Preset ID.
        preset_data: Preset update data.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with updated theme preset.
    """
    # Validate theme colors if config is provided
    if preset_data.config:
        validate_theme_colors(preset_data.config)

    preset_service = ThemePresetService(db)
    preset = preset_service.update_preset(
        preset_id=preset_id,
        tenant_id=current_user.tenant_id,
        name=preset_data.name,
        description=preset_data.description,
        config=preset_data.config,
        is_default=preset_data.is_default,
    )

    return StandardResponse(
        data=ThemePresetResponse.model_validate(preset),
        message="Theme preset updated successfully",
    )


@router.delete(
    "/app_theme/presets/{preset_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete theme preset",
    description="Delete a theme preset. System presets cannot be deleted. Requires config.edit permission.",
    responses={
        200: {"description": "Theme preset deleted successfully"},
        400: {
            "description": "Cannot delete system preset",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CANNOT_DELETE_SYSTEM_PRESET",
                            "message": "System presets cannot be deleted",
                            "details": {"preset_id": "...", "preset_name": "Original"},
                        }
                    }
                }
            },
        },
        403: {"description": "Insufficient permissions"},
        404: {"description": "Theme preset not found"},
    },
)
async def delete_theme_preset(
    preset_id: UUID,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Delete a theme preset.

    System presets cannot be deleted.

    Requires: config.edit

    Args:
        preset_id: Preset ID.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with success message.
    """
    preset_service = ThemePresetService(db)
    preset_service.delete_preset(preset_id, current_user.tenant_id)

    return StandardResponse(
        data={"preset_id": str(preset_id)},
        message="Theme preset deleted successfully",
    )


@router.post(
    "/app_theme/presets/{preset_id}/apply",
    response_model=StandardResponse[ModuleConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Apply theme preset",
    description="Apply a theme preset as the active theme. Requires config.edit permission.",
    responses={
        200: {"description": "Theme preset applied successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Theme preset not found"},
    },
)
async def apply_theme_preset(
    preset_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ModuleConfigResponse]:
    """
    Apply a theme preset as the active theme.

    Requires: config.edit

    Args:
        preset_id: Preset ID.
        request: FastAPI request object (for audit).
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with applied theme configuration.
    """
    preset_service = ThemePresetService(db)
    config = preset_service.apply_preset(preset_id, current_user.tenant_id)

    # Also update via ConfigService to ensure audit logging
    config_service = ConfigService(db)
    ip_address, user_agent = get_client_info(request)
    config_service.set_module_config(
        tenant_id=current_user.tenant_id,
        module="app_theme",
        config_dict=config,
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=ModuleConfigResponse(module="app_theme", config=config),
        message="Theme preset applied successfully",
    )


@router.put(
    "/app_theme/presets/{preset_id}/set-default",
    response_model=StandardResponse[ThemePresetResponse],
    status_code=status.HTTP_200_OK,
    summary="Set default theme preset",
    description="Set a theme preset as the default for the tenant. Requires config.edit permission.",
    responses={
        200: {"description": "Default preset set successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Theme preset not found"},
    },
)
async def set_default_theme_preset(
    preset_id: UUID,
    current_user: Annotated[User, Depends(require_permission("config.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ThemePresetResponse]:
    """
    Set a theme preset as the default for the tenant.

    Requires: config.edit

    Args:
        preset_id: Preset ID.
        current_user: Current authenticated user (must have config.edit).
        db: Database session.

    Returns:
        StandardResponse with updated preset.
    """
    preset_service = ThemePresetService(db)
    preset = preset_service.set_default_preset(preset_id, current_user.tenant_id)

    return StandardResponse(
        data=ThemePresetResponse.model_validate(preset),
        message="Default preset set successfully",
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

    if key in color_keys or (key.startswith("dark_") and key.replace("dark_", "", 1) in color_keys):
        try:
            validate_color(key, config_update.value)
        except InvalidColorFormatException:
            # Re-raise to ensure FastAPI handles it correctly
            raise

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


# Files module configuration endpoints (MUST come before /{module} and /{module}/{key} routes)
# These endpoints are defined before the generic routes to ensure FastAPI matches them first
@router.get(
    "/files/storage",
    response_model=StandardResponse[StorageConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Get storage configuration",
    description="Get current storage configuration (Local/S3/Hybrid). Requires system.configure permission.",
)
async def get_storage_config(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[StorageConfigResponse]:
    """Get storage configuration."""
    from app.core.files.storage_config_service import StorageConfigService

    service = StorageConfigService(db)
    config = service.get_storage_config(current_user.tenant_id)

    return StandardResponse(
        data=StorageConfigResponse(**config),
        message="Storage configuration retrieved successfully",
    )


@router.put(
    "/files/storage",
    response_model=StandardResponse[StorageConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Update storage configuration",
    description="Update storage configuration. Requires system.configure permission.",
)
async def update_storage_config(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
    config_data: StorageConfigUpdate,
    request: Request,
) -> StandardResponse[StorageConfigResponse]:
    """Update storage configuration."""
    from app.core.files.storage_config_service import StorageConfigService
    from app.core.logging import get_client_info

    service = StorageConfigService(db)
    ip_address, user_agent = get_client_info(request)

    updated_config = service.update_storage_config(
        tenant_id=current_user.tenant_id,
        config=config_data.model_dump(),
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=StorageConfigResponse(**updated_config),
        message="Storage configuration updated successfully",
    )


@router.post(
    "/files/storage/test",
    response_model=StandardResponse[S3ConnectionTestResponse],
    status_code=status.HTTP_200_OK,
    summary="Test S3 connection",
    description="Test S3 connection with provided credentials. Requires system.configure permission.",
)
async def test_s3_connection(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
    test_data: S3ConnectionTestRequest,
) -> StandardResponse[S3ConnectionTestResponse]:
    """Test S3 connection."""
    from app.core.files.storage_config_service import StorageConfigService

    service = StorageConfigService(db)
    result = await service.test_s3_connection(
        tenant_id=current_user.tenant_id,
        config=test_data.model_dump(),
    )

    return StandardResponse(
        data=S3ConnectionTestResponse(**result),
        message="S3 connection test completed",
    )


@router.get(
    "/files/stats",
    response_model=StandardResponse[StorageStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get storage statistics",
    description="Get storage statistics (space used, file counts, distributions). Requires system.configure permission.",
)
async def get_storage_stats(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[StorageStatsResponse]:
    """Get storage statistics."""
    import logging

    logger = logging.getLogger(__name__)
    from app.core.files.storage_config_service import StorageConfigService

    try:
        service = StorageConfigService(db)
        stats = service.get_storage_stats(current_user.tenant_id)

        return StandardResponse(
            data=StorageStatsResponse(**stats),
            message="Storage statistics retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error retrieving storage stats for tenant {current_user.tenant_id}: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="STATS_RETRIEVAL_FAILED",
            message=f"Failed to retrieve storage statistics: {str(e)}",
        )


@router.get(
    "/files/limits",
    response_model=StandardResponse[FileLimitsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get file limits",
    description="Get file limits configuration. Requires system.configure permission.",
)
async def get_file_limits(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[FileLimitsResponse]:
    """Get file limits configuration."""
    from app.core.files.storage_config_service import StorageConfigService

    service = StorageConfigService(db)
    limits = service.get_file_limits(current_user.tenant_id)

    return StandardResponse(
        data=FileLimitsResponse(**limits),
        message="File limits retrieved successfully",
    )


@router.put(
    "/files/limits",
    response_model=StandardResponse[FileLimitsResponse],
    status_code=status.HTTP_200_OK,
    summary="Update file limits",
    description="Update file limits configuration. Requires system.configure permission.",
)
async def update_file_limits(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
    limits_data: FileLimitsUpdate,
    request: Request,
) -> StandardResponse[FileLimitsResponse]:
    """Update file limits configuration."""
    from app.core.files.storage_config_service import StorageConfigService
    from app.core.logging import get_client_info

    service = StorageConfigService(db)
    ip_address, user_agent = get_client_info(request)

    updated_limits = service.update_file_limits(
        tenant_id=current_user.tenant_id,
        limits=limits_data.model_dump(exclude_unset=True),
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=FileLimitsResponse(**updated_limits),
        message="File limits updated successfully",
    )


@router.get(
    "/files/thumbnails",
    response_model=StandardResponse[ThumbnailConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Get thumbnail configuration",
    description="Get thumbnail configuration. Requires system.configure permission.",
)
async def get_thumbnail_config(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[ThumbnailConfigResponse]:
    """Get thumbnail configuration."""
    from app.core.files.storage_config_service import StorageConfigService

    service = StorageConfigService(db)
    config = service.get_thumbnail_config(current_user.tenant_id)

    return StandardResponse(
        data=ThumbnailConfigResponse(**config),
        message="Thumbnail configuration retrieved successfully",
    )


@router.put(
    "/files/thumbnails",
    response_model=StandardResponse[ThumbnailConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="Update thumbnail configuration",
    description="Update thumbnail configuration. Requires system.configure permission.",
)
async def update_thumbnail_config(
    current_user: Annotated[User, Depends(require_permission("system.configure"))],
    db: Annotated[Session, Depends(get_db)],
    config_data: ThumbnailConfigUpdate,
    request: Request,
) -> StandardResponse[ThumbnailConfigResponse]:
    """Update thumbnail configuration."""
    from app.core.files.storage_config_service import StorageConfigService
    from app.core.logging import get_client_info

    # Validate quality range manually to return proper error code
    if config_data.quality is not None and (config_data.quality < 1 or config_data.quality > 100):
        raise_bad_request(
            "INVALID_QUALITY",
            "Quality must be between 1 and 100"
        )

    service = StorageConfigService(db)
    ip_address, user_agent = get_client_info(request)

    updated_config = service.update_thumbnail_config(
        tenant_id=current_user.tenant_id,
        config=config_data.model_dump(exclude_unset=True),
        user_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return StandardResponse(
        data=ThumbnailConfigResponse(**updated_config),
        message="Thumbnail configuration updated successfully",
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
        try:
            validate_color(key, config_update.value)
        except InvalidColorFormatException:
            # Re-raise to ensure FastAPI handles it correctly
            raise

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
    notifications_config = config_service.get_module_config(current_user.tenant_id, "notifications")
    smtp_data = {}
    for key, value in notifications_config.items():
        if key.startswith("channels.smtp."):
            config_key = key.replace("channels.smtp.", "")
            smtp_data[config_key] = value

    if not smtp_data.get("enabled", False):
        raise_bad_request(
            "SMTP_NOT_ENABLED",
            "SMTP channel is not enabled",
        )

    # Test SMTP connection
    from app.core.notifications.smtp_test import check_smtp_connection

    test_result = check_smtp_connection(smtp_data)

    if not test_result.success:
        raise_bad_request(
            "SMTP_CONNECTION_FAILED",
            test_result.message,
            details={"error": test_result.error, "details": test_result.details},
        )

    return StandardResponse(
        data={
            "success": test_result.success,
            "message": test_result.message,
            "details": test_result.details,
        },
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
    # Prevent this generic endpoint from handling files module specific routes
    # These should be handled by the specific /files/* endpoints defined above
    if module == "files" and key in ("storage", "limits", "thumbnails", "stats"):
        raise APIException(
            code="ENDPOINT_NOT_FOUND",
            message=f"Endpoint '/config/{module}/{key}' not found. Use the specific endpoint instead.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"module": module, "key": key},
        )

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
        StandardResponse confirming deletion.

    Raises:
        APIException: If user lacks permission or configuration not found.
    """
    # Prevent this generic endpoint from handling files module specific routes
    # These should be handled by the specific /files/* endpoints defined above
    if module == "files" and key in ("storage", "limits", "thumbnails", "stats"):
        raise APIException(
            code="ENDPOINT_NOT_FOUND",
            message=f"Endpoint '/config/{module}/{key}' not found. Use the specific endpoint instead.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"module": module, "key": key},
        )

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

    config_service.delete(
        tenant_id=current_user.tenant_id, module=module, key=key
    )

    return StandardResponse(
        data={
            "module": module,
            "key": key,
            "deleted": True,
            "message": f"Configuration value '{module}.{key}' deleted successfully",
        }
    )

