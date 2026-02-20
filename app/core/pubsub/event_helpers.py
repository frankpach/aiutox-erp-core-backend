"""Helper functions for publishing events safely in sync contexts."""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_publish_event(
    event_publisher: Any,
    event_type: str,
    entity_type: str,
    entity_id: Any,
    tenant_id: Any,
    user_id: Any | None = None,
    metadata: Any | None = None,
) -> None:
    """
    Safely publish an event, handling both sync and async contexts.

    This function attempts to publish an event in a way that works in both
    synchronous (tests, CLI) and asynchronous (FastAPI endpoints) contexts.

    Args:
        event_publisher: EventPublisher instance.
        event_type: Type of event (e.g., "task.created").
        entity_type: Type of entity (e.g., "task").
        entity_id: ID of the entity.
        tenant_id: Tenant ID.
        user_id: Optional user ID.
        metadata: Optional event metadata.
    """
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # Loop is running, schedule as task
            asyncio.create_task(
                event_publisher.publish(
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=metadata,
                )
            )
        except RuntimeError:
            # No running loop, try to get or create one
            try:
                # Try to get existing event loop (new way, no deprecation)
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    # Loop is running, use create_task
                    asyncio.create_task(
                        event_publisher.publish(
                            event_type=event_type,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=metadata,
                        )
                    )
                else:
                    # Loop exists but not running, run until complete
                    loop.run_until_complete(
                        event_publisher.publish(
                            event_type=event_type,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=metadata,
                        )
                    )
            except (RuntimeError, AttributeError):
                # No event loop at all, try to create new one
                # In test contexts, this might fail, so we skip silently
                try:
                    asyncio.run(
                        event_publisher.publish(
                            event_type=event_type,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=metadata,
                        )
                    )
                except RuntimeError:
                    # Can't create event loop (e.g., in test context)
                    # Skip silently - events are not critical for tests
                    pass
    except Exception as e:
        # Log warning but don't fail - events are fire-and-forget
        logger.debug(f"Failed to publish {event_type} event: {e}")
