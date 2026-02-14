"""Inventory module domain events."""

from __future__ import annotations

INVENTORY_STOCK_LOW = "inventory.stock_low"
INVENTORY_MOVEMENT_CREATED = "inventory.movement.created"

PUBLISHED_EVENTS = [
    INVENTORY_STOCK_LOW,
    INVENTORY_MOVEMENT_CREATED,
]
