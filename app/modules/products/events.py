"""Product module domain events."""

from __future__ import annotations

PRODUCT_CREATED = "product.created"
PRODUCT_UPDATED = "product.updated"
PRODUCT_DELETED = "product.deleted"

PUBLISHED_EVENTS = [
    PRODUCT_CREATED,
    PRODUCT_UPDATED,
    PRODUCT_DELETED,
]
