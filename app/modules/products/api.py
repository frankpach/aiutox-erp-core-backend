"""Product management router for CRUD operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import (
    raise_bad_request,
    raise_conflict,
    raise_forbidden,
    raise_not_found,
)
from app.core.logging import get_client_info
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.user import User
from app.modules.products.repositories.product_repository import CategoryRepository
from app.modules.products.schemas.product import (
    CategoryCreate,
    CategoryUpdate,
    ProductBarcodeCreate,
    ProductBarcodeUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
)
from app.modules.products.services.product_service import ProductService
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse

router = APIRouter()


# Product endpoints
# IMPORTANT: Specific routes (like /categories, /variants, /barcodes) must come BEFORE
# parameterized routes (like /{product_id}) to avoid route conflicts


@router.get(
    "",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List products",
    description="List all products in the current tenant. Requires products.view permission.",
    responses={
        200: {"description": "List of products retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_products(
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    category_id: UUID | None = Query(None, description="Filter by category ID"),
    search: str | None = Query(None, description="Search by name or SKU"),
) -> StandardListResponse[dict]:
    """
    List all products in the current tenant.

    Requires: products.view

    Args:
        current_user: Current authenticated user (must have products.view).
        db: Database session.
        page: Page number (default: 1).
        page_size: Page size (default: 20, max: 100).
        category_id: Optional category filter.
        search: Optional search query (searches name and SKU).

    Returns:
        StandardListResponse with list of products and pagination metadata.
    """
    product_service = ProductService(db)
    skip = (page - 1) * page_size
    products, total = product_service.list_products(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=page_size,
        category_id=category_id,
        search=search,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=products,
        meta=PaginationMeta(
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ),
    )


# Category endpoints (must come before /{product_id} to avoid route conflicts)
@router.get(
    "/categories",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List categories",
    description="List all categories in the current tenant. Requires products.view permission.",
    responses={
        200: {"description": "List of categories retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_categories(
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[dict]:
    """
    List all categories in the current tenant.

    Requires: products.view

    Args:
        current_user: Current authenticated user (must have products.view).
        db: Database session.
        page: Page number (default: 1).
        page_size: Page size (default: 20, max: 100).

    Returns:
        StandardListResponse with list of categories and pagination metadata.
    """
    product_service = ProductService(db)
    skip = (page - 1) * page_size
    categories, total = product_service.list_categories(
        tenant_id=current_user.tenant_id, skip=skip, limit=page_size
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=categories,
        meta=PaginationMeta(
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ),
    )


@router.get(
    "/by-barcode/{barcode}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get product by barcode",
    description="Get product or variant by barcode. Requires products.view permission.",
    responses={
        200: {"description": "Product or variant retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Product or variant not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "message": "Product or variant not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def get_by_barcode(
    barcode: str,
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Get product or variant by barcode.

    Requires: products.view

    Args:
        barcode: Barcode value.
        current_user: Current authenticated user (must have products.view).
        db: Database session.

    Returns:
        StandardResponse with product or variant data.
    """
    product_service = ProductService(db)
    result = product_service.get_by_barcode(current_user.tenant_id, barcode)

    if not result:
        raise_not_found("Product", None)

    return StandardResponse(data=result)


@router.get(
    "/categories/{category_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get category",
    description="Get category by ID. Requires products.view permission.",
    responses={
        200: {"description": "Category retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CATEGORY_NOT_FOUND",
                            "message": "Category not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def get_category(
    category_id: str,
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Get category by ID.

    Requires: products.view

    Args:
        category_id: Category UUID.
        current_user: Current authenticated user (must have products.view).
        db: Database session.

    Returns:
        StandardResponse with category data.
    """
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid category ID format")

    product_service = ProductService(db)
    category_repo = CategoryRepository(db)
    category = category_repo.get_category_by_id(category_uuid, current_user.tenant_id)

    if not category:
        raise_not_found("Category", category_id)

    category_dict = product_service._category_to_dict(category)
    return StandardResponse(data=category_dict)


@router.post(
    "/categories",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new category. Requires products.create permission.",
    responses={
        201: {"description": "Category created successfully"},
        400: {
            "description": "Invalid request or category already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CATEGORY_ALREADY_EXISTS",
                            "message": "Category with slug 'electronics' already exists",
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
                            "details": {"required_permission": "products.create"},
                        }
                    }
                }
            },
        },
    },
)
async def create_category(
    category_data: CategoryCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.create"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Create a new category.

    Requires: products.create

    Args:
        category_data: Category creation data.
        current_user: Current authenticated user (must have products.create).
        db: Database session.

    Returns:
        StandardResponse with created category data.
    """
    # Ensure category is created in the same tenant as current user
    if category_data.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot create category in different tenant",
        )

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        category = product_service.create_category(
            category_data,
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return StandardResponse(data=category)
    except ValueError as e:
        raise_conflict(code="CATEGORY_ALREADY_EXISTS", message=str(e))


@router.patch(
    "/categories/{category_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update category",
    description="Update category by ID. Requires products.edit permission.",
    responses={
        200: {"description": "Category updated successfully"},
        400: {
            "description": "Invalid request or category already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CATEGORY_ALREADY_EXISTS",
                            "message": "Category with slug 'electronics' already exists",
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
                            "details": {"required_permission": "products.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CATEGORY_NOT_FOUND",
                            "message": "Category not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Update category by ID.

    Requires: products.edit

    Args:
        category_id: Category UUID.
        category_data: Category update data.
        current_user: Current authenticated user (must have products.edit).
        db: Database session.

    Returns:
        StandardResponse with updated category data.
    """
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid category ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        updated_category = product_service.update_category(
            category_uuid,
            category_data,
            tenant_id=current_user.tenant_id,
            updated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not updated_category:
            raise_not_found("Category", category_id)
        return StandardResponse(data=updated_category)
    except ValueError as e:
        raise_conflict(code="CATEGORY_ALREADY_EXISTS", message=str(e))


@router.delete(
    "/categories/{category_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete category",
    description="Delete category by ID. Requires products.delete permission.",
    responses={
        200: {"description": "Category deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.delete"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "CATEGORY_NOT_FOUND",
                            "message": "Category not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def delete_category(
    category_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.delete"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Delete category by ID.

    Requires: products.delete

    Args:
        category_id: Category UUID.
        current_user: Current authenticated user (must have products.delete).
        db: Database session.

    Returns:
        StandardResponse with success message.
    """
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid category ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    success = product_service.delete_category(
        category_uuid,
        tenant_id=current_user.tenant_id,
        deleted_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not success:
        raise_not_found("Category", category_id)

    return StandardResponse(data={"message": "Category deleted successfully"})


@router.get(
    "/{product_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get product",
    description="Get product by ID. Requires products.view permission.",
    responses={
        200: {"description": "Product retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Product not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "message": "Product not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def get_product(
    product_id: str,
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Get product by ID.

    Requires: products.view

    Args:
        product_id: Product UUID.
        current_user: Current authenticated user (must have products.view).
        db: Database session.

    Returns:
        StandardResponse with product data.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    product_service = ProductService(db)
    product = product_service.get_product(product_uuid, current_user.tenant_id)

    if not product:
        raise_not_found("Product", product_id)

    return StandardResponse(data=product)


@router.post(
    "",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Create a new product. Requires products.create permission.",
    responses={
        201: {"description": "Product created successfully"},
        400: {
            "description": "Invalid request or product already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_ALREADY_EXISTS",
                            "message": "Product with SKU 'ABC123' already exists",
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
                            "details": {"required_permission": "products.create"},
                        }
                    }
                }
            },
        },
    },
)
async def create_product(
    product_data: ProductCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_permission("products.create"))],
    db: Annotated[Session, Depends(get_db)],
    event_publisher: Annotated[EventPublisher, Depends(get_event_publisher)] = None,
) -> StandardResponse[dict]:
    """
    Create a new product.

    Requires: products.create

    Args:
        product_data: Product creation data.
        current_user: Current authenticated user (must have products.create).
        db: Database session.
        background_tasks: FastAPI background tasks.
        event_publisher: Event publisher instance.

    Returns:
        StandardResponse with created product data.
    """
    # Ensure product is created in the same tenant as current user
    if product_data.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot create product in different tenant",
        )

    product_service = ProductService(db, event_publisher=event_publisher)
    ip_address, user_agent = get_client_info(request)
    try:
        product = product_service.create_product(
            product_data,
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Publish event in background
        if event_publisher:
            # product["id"] is already a UUID object, not a string
            product_id = (
                product["id"]
                if isinstance(product["id"], UUID)
                else UUID(str(product["id"]))
            )
            background_tasks.add_task(
                event_publisher.publish,
                event_type="product.created",
                entity_type="product",
                entity_id=product_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                metadata=EventMetadata(
                    source="product_service",
                    version="1.0",
                    additional_data={
                        "product_name": product.get("name"),
                        "sku": product.get("sku"),
                    },
                ),
            )

        return StandardResponse(data=product)
    except ValueError as e:
        error_msg = str(e)
        # Check for specific validation errors
        if "SKU must be alphanumeric" in error_msg:
            raise_bad_request(code="INVALID_SKU_FORMAT", message=error_msg)
        elif "Currency" in error_msg or "not supported" in error_msg:
            raise_bad_request(code="INVALID_CURRENCY", message=error_msg)
        elif "already exists" in error_msg:
            raise_conflict(code="PRODUCT_ALREADY_EXISTS", message=error_msg)
        else:
            raise_bad_request(code="VALIDATION_ERROR", message=error_msg)


@router.patch(
    "/{product_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update product",
    description="Update product by ID. Requires products.edit permission.",
    responses={
        200: {"description": "Product updated successfully"},
        400: {
            "description": "Invalid request or product already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_ALREADY_EXISTS",
                            "message": "Product with SKU 'ABC123' already exists",
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
                            "details": {"required_permission": "products.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Product not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "message": "Product not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_permission("products.edit"))],
    db: Annotated[Session, Depends(get_db)],
    event_publisher: Annotated[EventPublisher, Depends(get_event_publisher)] = None,
) -> StandardResponse[dict]:
    """
    Update product by ID.

    Requires: products.edit

    Args:
        product_id: Product UUID.
        product_data: Product update data.
        current_user: Current authenticated user (must have products.edit).
        db: Database session.
        background_tasks: FastAPI background tasks.
        event_publisher: Event publisher instance.

    Returns:
        StandardResponse with updated product data.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    product_service = ProductService(db, event_publisher=event_publisher)
    ip_address, user_agent = get_client_info(request)
    try:
        updated_product = product_service.update_product(
            product_uuid,
            product_data,
            tenant_id=current_user.tenant_id,
            updated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not updated_product:
            raise_not_found("Product", product_id)

        # Publish event in background
        if event_publisher:
            background_tasks.add_task(
                event_publisher.publish,
                event_type="product.updated",
                entity_type="product",
                entity_id=product_uuid,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                metadata=EventMetadata(
                    source="product_service",
                    version="1.0",
                    additional_data={
                        "product_name": updated_product.get("name"),
                        "sku": updated_product.get("sku"),
                    },
                ),
            )

        return StandardResponse(data=updated_product)
    except ValueError as e:
        error_msg = str(e)
        # Check for specific validation errors
        if "SKU must be alphanumeric" in error_msg:
            raise_bad_request(code="INVALID_SKU_FORMAT", message=error_msg)
        elif "Currency" in error_msg or "not supported" in error_msg:
            raise_bad_request(code="INVALID_CURRENCY", message=error_msg)
        elif "already exists" in error_msg:
            raise_conflict(code="PRODUCT_ALREADY_EXISTS", message=error_msg)
        else:
            raise_bad_request(code="VALIDATION_ERROR", message=error_msg)


@router.delete(
    "/{product_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete product (soft delete)",
    description="Soft delete product by setting is_active=False. Requires products.delete permission.",
    responses={
        200: {"description": "Product deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.delete"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Product not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "message": "Product not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def delete_product(
    product_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_permission("products.delete"))],
    db: Annotated[Session, Depends(get_db)],
    event_publisher: Annotated[EventPublisher, Depends(get_event_publisher)] = None,
) -> StandardResponse[dict]:
    """
    Soft delete product by setting is_active=False.

    Requires: products.delete

    Args:
        product_id: Product UUID.
        current_user: Current authenticated user (must have products.delete).
        db: Database session.
        background_tasks: FastAPI background tasks.
        event_publisher: Event publisher instance.

    Returns:
        StandardResponse with success message.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    # Get product info before deletion for event
    product_service = ProductService(db, event_publisher=event_publisher)
    product = product_service.get_product(product_uuid, current_user.tenant_id)

    ip_address, user_agent = get_client_info(request)
    success = product_service.delete_product(
        product_uuid,
        tenant_id=current_user.tenant_id,
        deleted_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not success:
        raise_not_found("Product", product_id)

    # Publish event in background
    if event_publisher and product:
        background_tasks.add_task(
            event_publisher.publish,
            event_type="product.deleted",
            entity_type="product",
            entity_id=product_uuid,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            metadata=EventMetadata(
                source="product_service",
                version="1.0",
                additional_data={
                    "product_name": product.get("name"),
                    "sku": product.get("sku"),
                },
            ),
        )

    return StandardResponse(data={"message": "Product deleted successfully"})


# Variant endpoints
@router.get(
    "/{product_id}/variants",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List product variants",
    description="List all variants for a product. Requires products.view permission.",
    responses={
        200: {"description": "List of variants retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_variants(
    product_id: str,
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[dict]:
    """
    List all variants for a product.

    Requires: products.view

    Args:
        product_id: Product UUID.
        current_user: Current authenticated user (must have products.view).
        db: Database session.

    Returns:
        StandardListResponse with list of variants.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    product_service = ProductService(db)
    variants = product_service.list_variants(product_uuid, current_user.tenant_id)
    total = len(variants)

    return StandardListResponse(
        data=variants,
        meta=PaginationMeta(
            total=total,
            page=1,
            page_size=max(total, 1) if total > 0 else 20,
            total_pages=1 if total > 0 else 0,
        ),
    )


@router.post(
    "/{product_id}/variants",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create product variant",
    description="Create a new variant for a product. Requires products.create permission.",
    responses={
        201: {"description": "Variant created successfully"},
        400: {
            "description": "Invalid request or variant already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VARIANT_ALREADY_EXISTS",
                            "message": "Variant with SKU 'ABC123-RED' already exists for this product",
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
                            "details": {"required_permission": "products.create"},
                        }
                    }
                }
            },
        },
    },
)
async def create_variant(
    product_id: str,
    variant_data: ProductVariantCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.create"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Create a new variant for a product.

    Requires: products.create

    Args:
        product_id: Product UUID.
        variant_data: Variant creation data.
        current_user: Current authenticated user (must have products.create).
        db: Database session.

    Returns:
        StandardResponse with created variant data.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        variant = product_service.create_variant(
            product_uuid,
            variant_data,
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return StandardResponse(data=variant)
    except ValueError as e:
        raise_conflict(code="VARIANT_ALREADY_EXISTS", message=str(e))


@router.patch(
    "/variants/{variant_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update product variant",
    description="Update variant by ID. Requires products.edit permission.",
    responses={
        200: {"description": "Variant updated successfully"},
        400: {
            "description": "Invalid request or variant already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VARIANT_ALREADY_EXISTS",
                            "message": "Variant with SKU 'ABC123-RED' already exists for this product",
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
                            "details": {"required_permission": "products.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Variant not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VARIANT_NOT_FOUND",
                            "message": "Variant not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def update_variant(
    variant_id: str,
    variant_data: ProductVariantUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Update variant by ID.

    Requires: products.edit

    Args:
        variant_id: Variant UUID.
        variant_data: Variant update data.
        current_user: Current authenticated user (must have products.edit).
        db: Database session.

    Returns:
        StandardResponse with updated variant data.
    """
    try:
        variant_uuid = UUID(variant_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid variant ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        updated_variant = product_service.update_variant(
            variant_uuid,
            variant_data,
            tenant_id=current_user.tenant_id,
            updated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not updated_variant:
            raise_not_found("Variant", variant_id)
        return StandardResponse(data=updated_variant)
    except ValueError as e:
        raise_conflict(code="VARIANT_ALREADY_EXISTS", message=str(e))


@router.delete(
    "/variants/{variant_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete product variant",
    description="Delete variant by ID. Requires products.delete permission.",
    responses={
        200: {"description": "Variant deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.delete"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Variant not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "VARIANT_NOT_FOUND",
                            "message": "Variant not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def delete_variant(
    variant_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.delete"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Delete variant by ID.

    Requires: products.delete

    Args:
        variant_id: Variant UUID.
        current_user: Current authenticated user (must have products.delete).
        db: Database session.

    Returns:
        StandardResponse with success message.
    """
    try:
        variant_uuid = UUID(variant_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid variant ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    success = product_service.delete_variant(
        variant_uuid,
        tenant_id=current_user.tenant_id,
        deleted_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not success:
        raise_not_found("Variant", variant_id)

    return StandardResponse(data={"message": "Variant deleted successfully"})


# Barcode endpoints (/{product_id}/barcodes routes must come before /{product_id})
@router.get(
    "/{product_id}/barcodes",
    response_model=StandardListResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="List product barcodes",
    description="List all barcodes for a product. Requires products.view permission.",
    responses={
        200: {"description": "List of barcodes retrieved successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.view"},
                        }
                    }
                }
            },
        },
    },
)
async def list_barcodes(
    product_id: str,
    current_user: Annotated[User, Depends(require_permission("products.view"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardListResponse[dict]:
    """
    List all barcodes for a product.

    Requires: products.view

    Args:
        product_id: Product UUID.
        current_user: Current authenticated user (must have products.view).
        db: Database session.

    Returns:
        StandardListResponse with list of barcodes.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    product_service = ProductService(db)
    barcodes = product_service.list_barcodes(
        product_id=product_uuid, variant_id=None, tenant_id=current_user.tenant_id
    )

    total = len(barcodes)
    return StandardListResponse(
        data=barcodes,
        meta=PaginationMeta(
            total=total,
            page=1,
            page_size=max(total, 1) if total > 0 else 20,
            total_pages=1 if total > 0 else 0,
        ),
    )


@router.post(
    "/{product_id}/barcodes",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Create product barcode",
    description="Create a new barcode for a product. Requires products.create permission.",
    responses={
        201: {"description": "Barcode created successfully"},
        400: {
            "description": "Invalid request or barcode already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "BARCODE_ALREADY_EXISTS",
                            "message": "Barcode '1234567890123' already exists",
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
                            "details": {"required_permission": "products.create"},
                        }
                    }
                }
            },
        },
    },
)
async def create_barcode(
    product_id: str,
    barcode_data: ProductBarcodeCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.create"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Create a new barcode for a product.

    Requires: products.create

    Args:
        product_id: Product UUID.
        barcode_data: Barcode creation data.
        current_user: Current authenticated user (must have products.create).
        db: Database session.

    Returns:
        StandardResponse with created barcode data.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid product ID format")

    # Ensure barcode is created in the same tenant as current user
    if barcode_data.tenant_id != current_user.tenant_id:
        raise_forbidden(
            code="AUTH_TENANT_MISMATCH",
            message="Cannot create barcode in different tenant",
        )

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        barcode = product_service.create_barcode(
            product_id=product_uuid,
            variant_id=None,
            barcode_data=barcode_data,
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return StandardResponse(data=barcode)
    except ValueError as e:
        error_msg = str(e)
        # Check for specific validation errors
        if "EAN13" in error_msg or "UPC" in error_msg or "CODE128" in error_msg:
            raise_bad_request(code="INVALID_BARCODE_FORMAT", message=error_msg)
        elif "already exists" in error_msg:
            raise_conflict(code="BARCODE_ALREADY_EXISTS", message=error_msg)
        else:
            raise_bad_request(code="VALIDATION_ERROR", message=error_msg)


@router.patch(
    "/barcodes/{barcode_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Update product barcode",
    description="Update barcode by ID. Requires products.edit permission.",
    responses={
        200: {"description": "Barcode updated successfully"},
        400: {
            "description": "Invalid request or barcode already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "BARCODE_ALREADY_EXISTS",
                            "message": "Barcode '1234567890123' already exists",
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
                            "details": {"required_permission": "products.edit"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Barcode not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "BARCODE_NOT_FOUND",
                            "message": "Barcode not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def update_barcode(
    barcode_id: str,
    barcode_data: ProductBarcodeUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.edit"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Update barcode by ID.

    Requires: products.edit

    Args:
        barcode_id: Barcode UUID.
        barcode_data: Barcode update data.
        current_user: Current authenticated user (must have products.edit).
        db: Database session.

    Returns:
        StandardResponse with updated barcode data.
    """
    try:
        barcode_uuid = UUID(barcode_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid barcode ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    try:
        updated_barcode = product_service.update_barcode(
            barcode_uuid,
            barcode_data,
            tenant_id=current_user.tenant_id,
            updated_by=current_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not updated_barcode:
            raise_not_found("Barcode", barcode_id)
        return StandardResponse(data=updated_barcode)
    except ValueError as e:
        error_msg = str(e)
        # Check for specific validation errors
        if "EAN13" in error_msg or "UPC" in error_msg or "CODE128" in error_msg:
            raise_bad_request(code="INVALID_BARCODE_FORMAT", message=error_msg)
        elif "already exists" in error_msg:
            raise_conflict(code="BARCODE_ALREADY_EXISTS", message=error_msg)
        else:
            raise_bad_request(code="VALIDATION_ERROR", message=error_msg)


@router.delete(
    "/barcodes/{barcode_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete product barcode",
    description="Delete barcode by ID. Requires products.delete permission.",
    responses={
        200: {"description": "Barcode deleted successfully"},
        403: {
            "description": "Insufficient permissions",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "AUTH_INSUFFICIENT_PERMISSIONS",
                            "message": "Insufficient permissions",
                            "details": {"required_permission": "products.delete"},
                        }
                    }
                }
            },
        },
        404: {
            "description": "Barcode not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "BARCODE_NOT_FOUND",
                            "message": "Barcode not found",
                            "details": None,
                        }
                    }
                }
            },
        },
    },
)
async def delete_barcode(
    barcode_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_permission("products.delete"))],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[dict]:
    """
    Delete barcode by ID.

    Requires: products.delete

    Args:
        barcode_id: Barcode UUID.
        current_user: Current authenticated user (must have products.delete).
        db: Database session.

    Returns:
        StandardResponse with success message.
    """
    try:
        barcode_uuid = UUID(barcode_id)
    except ValueError:
        raise_bad_request(code="INVALID_UUID", message="Invalid barcode ID format")

    product_service = ProductService(db)
    ip_address, user_agent = get_client_info(request)
    success = product_service.delete_barcode(
        barcode_uuid,
        tenant_id=current_user.tenant_id,
        deleted_by=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if not success:
        raise_not_found("Barcode", barcode_id)

    return StandardResponse(data={"message": "Barcode deleted successfully"})
