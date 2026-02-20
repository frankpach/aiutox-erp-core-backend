"""Comment models for comments and collaboration management."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Comment(Base):
    """Comment model for polymorphic comments on any entity."""

    __tablename__ = "comments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Polymorphic relationship
    entity_type = Column(
        String(50), nullable=False, index=True
    )  # e.g., 'product', 'order', 'task'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Comment information
    content = Column(Text, nullable=False)
    parent_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # For threaded comments

    # Author
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Status
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(
        Boolean, default=False, nullable=False, index=True
    )  # Soft delete

    # Metadata
    meta_data = Column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    edited_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    parent = relationship("Comment", remote_side=[id], backref="replies")
    mentions = relationship(
        "CommentMention", back_populates="comment", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "CommentAttachment", back_populates="comment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_comments_entity", "entity_type", "entity_id"),
        Index("idx_comments_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_comments_parent", "parent_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, entity_type={self.entity_type}, entity_id={self.entity_id})>"


class CommentMention(Base):
    """Comment mention model for @user mentions."""

    __tablename__ = "comment_mentions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comment relationship
    comment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Mentioned user
    mentioned_user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    notification_sent = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    comment = relationship("Comment", back_populates="mentions")

    __table_args__ = (
        Index("idx_comment_mentions_comment", "comment_id", "mentioned_user_id"),
        Index("idx_comment_mentions_user", "mentioned_user_id", "notification_sent"),
    )

    def __repr__(self) -> str:
        return f"<CommentMention(id={self.id}, comment_id={self.comment_id}, user_id={self.mentioned_user_id})>"


class CommentAttachment(Base):
    """Comment attachment model for file attachments in comments."""

    __tablename__ = "comment_attachments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comment relationship
    comment_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File relationship
    file_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    comment = relationship("Comment", back_populates="attachments")

    __table_args__ = (
        Index("idx_comment_attachments_comment", "comment_id", "file_id"),
    )

    def __repr__(self) -> str:
        return f"<CommentAttachment(id={self.id}, comment_id={self.comment_id}, file_id={self.file_id})>"
