"""Comment repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.comment import Comment, CommentAttachment, CommentMention


class CommentRepository:
    """Repository for comment data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Comment methods
    def create_comment(self, comment_data: dict) -> Comment:
        """Create a new comment."""
        comment = Comment(**comment_data)
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_comment_by_id(self, comment_id: UUID, tenant_id: UUID) -> Comment | None:
        """Get comment by ID and tenant."""
        return (
            self.db.query(Comment)
            .filter(Comment.id == comment_id, Comment.tenant_id == tenant_id)
            .first()
        )

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
        query = self.db.query(Comment).filter(
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
            Comment.tenant_id == tenant_id,
        )

        if not include_deleted:
            query = query.filter(not Comment.is_deleted)

        return query.order_by(Comment.created_at.asc()).offset(skip).limit(limit).all()

    def get_comment_thread(
        self, parent_id: UUID, tenant_id: UUID, include_deleted: bool = False
    ) -> list[Comment]:
        """Get comment thread (replies to a comment)."""
        query = self.db.query(Comment).filter(
            Comment.parent_id == parent_id, Comment.tenant_id == tenant_id
        )

        if not include_deleted:
            query = query.filter(not Comment.is_deleted)

        return query.order_by(Comment.created_at.asc()).all()

    def update_comment(self, comment: Comment, comment_data: dict) -> Comment:
        """Update comment."""
        for key, value in comment_data.items():
            setattr(comment, key, value)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment: Comment) -> None:
        """Soft delete comment."""
        from datetime import UTC, datetime

        self.update_comment(
            comment,
            {
                "is_deleted": True,
                "deleted_at": datetime.now(UTC),
            },
        )

    # Comment Mention methods
    def create_comment_mention(self, mention_data: dict) -> CommentMention:
        """Create a new comment mention."""
        mention = CommentMention(**mention_data)
        self.db.add(mention)
        self.db.commit()
        self.db.refresh(mention)
        return mention

    def get_mentions_by_comment(
        self, comment_id: UUID, tenant_id: UUID
    ) -> list[CommentMention]:
        """Get mentions by comment."""
        return (
            self.db.query(CommentMention)
            .filter(
                CommentMention.comment_id == comment_id,
                CommentMention.tenant_id == tenant_id,
            )
            .all()
        )

    def get_unnotified_mentions(
        self, tenant_id: UUID, user_id: UUID | None = None
    ) -> list[CommentMention]:
        """Get unnotified mentions."""
        query = self.db.query(CommentMention).filter(
            CommentMention.tenant_id == tenant_id,
            not CommentMention.notification_sent,
        )

        if user_id:
            query = query.filter(CommentMention.mentioned_user_id == user_id)

        return query.all()

    def mark_mention_notified(self, mention: CommentMention) -> CommentMention:
        """Mark mention as notified."""
        mention.notification_sent = True
        self.db.commit()
        self.db.refresh(mention)
        return mention

    # Comment Attachment methods
    def create_comment_attachment(
        self, attachment_data: dict
    ) -> CommentAttachment:
        """Create a new comment attachment."""
        attachment = CommentAttachment(**attachment_data)
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def get_attachments_by_comment(
        self, comment_id: UUID, tenant_id: UUID
    ) -> list[CommentAttachment]:
        """Get attachments by comment."""
        return (
            self.db.query(CommentAttachment)
            .filter(
                CommentAttachment.comment_id == comment_id,
                CommentAttachment.tenant_id == tenant_id,
            )
            .all()
        )

    def delete_comment_attachment(self, attachment: CommentAttachment) -> None:
        """Delete comment attachment."""
        self.db.delete(attachment)
        self.db.commit()

