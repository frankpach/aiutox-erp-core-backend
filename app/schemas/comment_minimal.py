"""Minimal schemas for comment endpoints."""

from pydantic import BaseModel, Field


class CommentCreateMinimal(BaseModel):
    """Minimal schema for creating comments."""
    content: str = Field(..., min_length=1, description="Comment content")
    mentions: list[str] = Field(default_factory=list, description="List of mentioned user IDs")

    class Config:
        extra = "allow"  # Allow additional fields
