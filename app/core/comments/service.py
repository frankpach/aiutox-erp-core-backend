"""Comment service for comments and collaboration management."""

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.activities.service import ActivityService
from app.core.files.service import FileService
from app.core.notifications.service import NotificationService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.comment import Comment
from app.repositories.comment_repository import CommentRepository

logger = logging.getLogger(__name__)


class MentionParser:
    """Parser for @user mentions in comments."""

    MENTION_PATTERN = re.compile(r"@(\w+)")

    @staticmethod
    def extract_mentions(content: str) -> list[str]:
        """Extract @username mentions from content.

        Args:
            content: Comment content

        Returns:
            List of mentioned usernames
        """
        matches = MentionParser.MENTION_PATTERN.findall(content)
        return list(set(matches))  # Remove duplicates

    @staticmethod
    def find_user_ids_by_usernames(
        db: Session, usernames: list[str], tenant_id: UUID
    ) -> dict[str, UUID]:
        """Find user IDs by usernames.

        Args:
            db: Database session
            usernames: List of usernames
            tenant_id: Tenant ID

        Returns:
            Dictionary mapping username to user_id
        """
        from app.models.user import User

        users = (
            db.query(User)
            .filter(User.email.in_(usernames), User.tenant_id == tenant_id)
            .all()
        )

        return {user.email: user.id for user in users}


class CommentService:
    """Service for managing comments and collaboration."""

    def __init__(
        self,
        db: Session,
        file_service: FileService | None = None,
        notification_service: NotificationService | None = None,
        activity_service: ActivityService | None = None,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize comment service.

        Args:
            db: Database session
            file_service: FileService instance (for attachments)
            notification_service: NotificationService instance
            activity_service: ActivityService instance
            event_publisher: EventPublisher instance
        """
        self.db = db
        self.repository = CommentRepository(db)
        self.file_service = file_service or FileService(db)
        self.notification_service = notification_service or NotificationService(db)
        self.activity_service = activity_service or ActivityService(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self.mention_parser = MentionParser()

    def create_comment(
        self,
        comment_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Comment:
        """Create a new comment.

        Args:
            comment_data: Comment data
            tenant_id: Tenant ID
            user_id: User ID who created the comment

        Returns:
            Created Comment object
        """
        comment_data["tenant_id"] = tenant_id
        comment_data["created_by"] = user_id

        comment = self.repository.create_comment(comment_data)

        # Extract and process mentions
        mentions = self.mention_parser.extract_mentions(comment.content)
        if mentions:
            user_map = self.mention_parser.find_user_ids_by_usernames(
                self.db, mentions, tenant_id
            )

            for username, mentioned_user_id in user_map.items():
                self.repository.create_comment_mention(
                    {
                        "tenant_id": tenant_id,
                        "comment_id": comment.id,
                        "mentioned_user_id": mentioned_user_id,
                        "notification_sent": False,
                    }
                )

                # Send notification (async)
                try:
                    import asyncio

                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    if loop.is_running():
                        asyncio.create_task(
                            self.notification_service.send(
                                event_type="comment.mentioned",
                                recipient_id=mentioned_user_id,
                                channels=["in-app", "email"],
                                data={
                                    "comment_id": str(comment.id),
                                    "entity_type": comment.entity_type,
                                    "entity_id": str(comment.entity_id),
                                    "mentioned_by": str(user_id),
                                },
                                tenant_id=tenant_id,
                            )
                        )
                    else:
                        loop.run_until_complete(
                            self.notification_service.send(
                                event_type="comment.mentioned",
                                recipient_id=mentioned_user_id,
                                channels=["in-app", "email"],
                                data={
                                    "comment_id": str(comment.id),
                                    "entity_type": comment.entity_type,
                                    "entity_id": str(comment.entity_id),
                                    "mentioned_by": str(user_id),
                                },
                                tenant_id=tenant_id,
                            )
                        )
                except Exception as e:
                    logger.error(f"Failed to send mention notification: {e}")

        # Create activity
        try:
            self.activity_service.create_activity(
                entity_type=comment.entity_type,
                entity_id=comment.entity_id,
                activity_type="comment",
                title="Comment added",
                tenant_id=tenant_id,
                user_id=user_id,
                description=comment.content[:200],  # First 200 chars
            )
        except Exception as e:
            logger.error(f"Failed to create activity for comment: {e}")

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
                        event_type="comment.created",
                        entity_type="comment",
                        entity_id=comment.id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        metadata=EventMetadata(
                            source="comment_service",
                            version="1.0",
                            additional_data={
                                "entity_type": comment.entity_type,
                                "entity_id": str(comment.entity_id),
                                "has_mentions": len(mentions) > 0,
                            },
                        ),
                    )

        return comment

    def get_comment(self, comment_id: UUID, tenant_id: UUID) -> Comment | None:
        """Get comment by ID."""
        return self.repository.get_comment_by_id(comment_id, tenant_id)

    def get_comments_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Comment]:
        """Get comments by entity."""
        return self.repository.get_comments_by_entity(
            entity_type, entity_id, tenant_id, include_deleted, skip, limit
        )

    def get_comment_thread(
        self, parent_id: UUID, tenant_id: UUID, include_deleted: bool = False
    ) -> list[Comment]:
        """Get comment thread (replies)."""
        return self.repository.get_comment_thread(parent_id, tenant_id, include_deleted)

    def update_comment(
        self, comment_id: UUID, tenant_id: UUID, comment_data: dict
    ) -> Comment | None:
        """Update comment."""
        comment = self.repository.get_comment_by_id(comment_id, tenant_id)
        if not comment:
            return None

        update_data = {
            **comment_data,
            "is_edited": True,
            "edited_at": datetime.now(UTC),
        }

        updated_comment = self.repository.update_comment(comment, update_data)

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="comment.updated",
            entity_type="comment",
            entity_id=updated_comment.id,
            tenant_id=tenant_id,
            user_id=updated_comment.created_by,
            metadata=EventMetadata(
                source="comment_service",
                version="1.0",
                additional_data={
                    "entity_type": updated_comment.entity_type,
                    "entity_id": str(updated_comment.entity_id),
                },
            ),
        )

        return updated_comment

    def delete_comment(self, comment_id: UUID, tenant_id: UUID) -> bool:
        """Delete comment (soft delete)."""
        comment = self.repository.get_comment_by_id(comment_id, tenant_id)
        if not comment:
            return False

        self.repository.delete_comment(comment)

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="comment.deleted",
            entity_type="comment",
            entity_id=comment.id,
            tenant_id=tenant_id,
            user_id=comment.created_by,
            metadata=EventMetadata(
                source="comment_service",
                version="1.0",
                additional_data={
                    "entity_type": comment.entity_type,
                    "entity_id": str(comment.entity_id),
                },
            ),
        )

        return True

    def add_attachment(
        self,
        comment_id: UUID,
        file_id: UUID,
        tenant_id: UUID,
    ) -> Any:
        """Add attachment to comment."""
        return self.repository.create_comment_attachment(
            {
                "tenant_id": tenant_id,
                "comment_id": comment_id,
                "file_id": file_id,
            }
        )

    def get_attachments(
        self, comment_id: UUID, tenant_id: UUID
    ) -> list[Any]:
        """Get attachments for a comment."""
        return self.repository.get_attachments_by_comment(comment_id, tenant_id)

