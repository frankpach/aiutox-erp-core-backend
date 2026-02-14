"""RBAC permissions for products module."""

from __future__ import annotations

PRODUCTS_VIEW = "products.view"
PRODUCTS_MANAGE = "products.manage"
PRODUCTS_CREATE = "products.create"
PRODUCTS_UPDATE = "products.update"
PRODUCTS_DELETE = "products.delete"

PRODUCTS_PERMISSIONS = [
    PRODUCTS_VIEW,
    PRODUCTS_MANAGE,
    PRODUCTS_CREATE,
    PRODUCTS_UPDATE,
    PRODUCTS_DELETE,
]
