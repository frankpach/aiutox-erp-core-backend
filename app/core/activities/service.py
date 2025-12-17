"""Activity service for timeline management."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.activity import Activity
from app.repositories.activity_repository import ActivityRepository

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for activity management."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize activity service.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = ActivityRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def create_activity(
        self,
        entity_type: str,
        entity_id: UUID,
        activity_type: str,
        title: str,
        tenant_id: UUID,
        user_id: UUID,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Activity:
        """Create a new activity.

        Args:
            entity_type: Entity type (e.g., 'product', 'order')
            entity_id: Entity ID
            activity_type: Activity type (e.g., 'comment', 'call')
            title: Activity title
            tenant_id: Tenant ID
            user_id: User ID who created the activity
            description: Activity description (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created Activity object
        """
        activity = self.repository.create(
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "activity_type": activity_type,
                "title": title,
                "description": description,
                "user_id": user_id,
                "metadata": metadata,
            }
        )

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
                        event_type="activity.created",
                        entity_type="activity",
                        entity_id=activity.id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        metadata=EventMetadata(
                            source="activity_service",
                            version="1.0",
                            additional_data={
                                "activity_type": activity_type,
                                "entity_type": entity_type,
                                "entity_id": str(entity_id),
                            },
                        ),
                    )

        logger.info(f"Activity created: {activity.id} ({activity_type})")
        return activity

    def get_activities(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        activity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Get activities for an entity (timeline).

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID
            activity_type: Filter by activity type (optional)
            skip: Skip records
            limit: Limit records

        Returns:
            List of Activity objects
        """
        return self.repository.get_by_entity(
            entity_type, entity_id, tenant_id, activity_type, skip, limit
        )

    def update_activity(
        self,
        activity_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        title: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Activity | None:
        """Update an activity.

        Args:
            activity_id: Activity ID
            tenant_id: Tenant ID
            user_id: User ID (for authorization)
            title: New title (optional)
            description: New description (optional)
            metadata: New metadata (optional)

        Returns:
            Updated Activity object or None if not found
        """
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if metadata is not None:
            update_data["metadata"] = metadata

        activity = self.repository.update(activity_id, tenant_id, update_data)

        if activity:
            # Publish event (async, but don't await to avoid blocking)
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.event_publisher.publish(
                            event_type="activity.updated",
                            entity_type="activity",
                            entity_id=activity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="activity_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.event_publisher.publish(
                            event_type="activity.updated",
                            entity_type="activity",
                            entity_id=activity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="activity_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to publish activity.updated event: {e}")

        return activity

    def delete_activity(
        self, activity_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> bool:
        """Delete an activity.

        Args:
            activity_id: Activity ID
            tenant_id: Tenant ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted successfully
        """
        deleted = self.repository.delete(activity_id, tenant_id)

        if deleted:
            # Publish event (async, but don't await to avoid blocking)
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.event_publisher.publish(
                            event_type="activity.deleted",
                            entity_type="activity",
                            entity_id=activity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="activity_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
                else:
                    loop.run_until_complete(
                        self.event_publisher.publish(
                            event_type="activity.deleted",
                            entity_type="activity",
                            entity_id=activity_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                            metadata=EventMetadata(
                                source="activity_service",
                                version="1.0",
                                additional_data={},
                            ),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to publish activity.deleted event: {e}")

            logger.info(f"Activity deleted: {activity_id}")

        return deleted

    def search_activities(
        self,
        tenant_id: UUID,
        query: str,
        entity_type: str | None = None,
        activity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Search activities.

        Args:
            tenant_id: Tenant ID
            query: Search query text
            entity_type: Filter by entity type (optional)
            activity_type: Filter by activity type (optional)
            skip: Skip records
            limit: Limit records

        Returns:
            List of Activity objects matching the search
        """
        return self.repository.search(
            tenant_id, query, entity_type, activity_type, skip, limit
        )

