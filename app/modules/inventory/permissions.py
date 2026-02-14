"""RBAC permissions for inventory module."""

from __future__ import annotations

INVENTORY_VIEW = "inventory.view"
INVENTORY_MANAGE = "inventory.manage"
INVENTORY_ADJUST = "inventory.adjust"
INVENTORY_MOVEMENTS_VIEW = "inventory.movements.view"

INVENTORY_PERMISSIONS = [
    INVENTORY_VIEW,
    INVENTORY_MANAGE,
    INVENTORY_ADJUST,
    INVENTORY_MOVEMENTS_VIEW,
]
