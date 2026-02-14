"""CRM module domain events."""

from __future__ import annotations

CUSTOMER_CREATED = "customer.created"
CUSTOMER_CONTACT_LOGGED = "customer.contact.logged"

PUBLISHED_EVENTS = [
    CUSTOMER_CREATED,
    CUSTOMER_CONTACT_LOGGED,
]
