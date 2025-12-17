"""Comment schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Comment schemas
class CommentBase(BaseModel):
    """Base schema for comment."""

    entity_type: str = Field(..., description="Entity type (e.g., 'product', 'order')", max_length=50)
    entity_id: UUID = Field(..., description="Entity ID")
    content: str = Field(..., description="Comment content")
    parent_id: UUID | None = Field(None, description="Parent comment ID (for threaded comments)")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CommentCreate(CommentBase):
    """Schema for creating a comment."""

    pass


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    content: str = Field(..., description="Comment content")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CommentResponse(CommentBase):
    """Schema for comment response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Comment Mention schemas
class CommentMentionBase(BaseModel):
    """Base schema for comment mention."""

    comment_id: UUID = Field(..., description="Comment ID")
    mentioned_user_id: UUID = Field(..., description="Mentioned user ID")


class CommentMentionResponse(CommentMentionBase):
    """Schema for comment mention response."""

    id: UUID
    tenant_id: UUID
    notification_sent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Comment Attachment schemas
class CommentAttachmentBase(BaseModel):
    """Base schema for comment attachment."""

    comment_id: UUID = Field(..., description="Comment ID")
    file_id: UUID = Field(..., description="File ID")


class CommentAttachmentCreate(CommentAttachmentBase):
    """Schema for creating a comment attachment."""

    pass


class CommentAttachmentResponse(CommentAttachmentBase):
    """Schema for comment attachment response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)







