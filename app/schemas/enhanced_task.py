"""
Enhanced task schemas with robust validation
Following Pydantic V2 best practices for security
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class TaskCreateEnhanced(BaseModel):
    """Enhanced task creation schema with robust validation."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        strip_whitespace=True,
        description="Task title (1-200 characters)",
    )

    description: str | None = Field(
        None,
        max_length=2000,
        strip_whitespace=True,
        description="Task description (max 2000 characters)",
    )

    due_date: datetime | None = Field(
        None, gt=datetime.now(), description="Due date must be in the future"
    )

    priority: str = Field(
        "medium",
        pattern="^(low|medium|high|urgent)$",
        description="Task priority: low, medium, high, or urgent",
    )

    status: str = Field(
        "todo",
        pattern="^(todo|in_progress|review|done|cancelled)$",
        description="Task status",
    )

    assigned_to_id: UUID | None = Field(None, description="Assignee user ID")

    parent_task_id: UUID | None = Field(None, description="Parent task ID for subtasks")

    tags: list[str | None] = Field(None, max_items=10, description="Task tags (max 10)")

    metadata: dict | None = Field(
        None, max_length=1000, description="Additional metadata (max 1KB)"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title content."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")

        # Check for potentially dangerous content
        dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
        for pattern in dangerous_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Title contains potentially unsafe content")

        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate description content."""
        if v is None:
            return None

        # Check for potentially dangerous content
        dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
        for pattern in dangerous_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Description contains potentially unsafe content")

        return v.strip() if v else None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str | None]) -> list[str | None]:
        """Validate tags content."""
        if v is None:
            return None

        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                continue

            tag = tag.strip()
            if tag and len(tag) <= 50:
                # Check for dangerous content
                dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
                if not any(
                    pattern.lower() in tag.lower() for pattern in dangerous_patterns
                ):
                    validated_tags.append(tag)

        return validated_tags[:10]  # Ensure max 10 tags


class TaskUpdateEnhanced(BaseModel):
    """Enhanced task update schema with validation."""

    title: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        strip_whitespace=True,
        description="Task title (1-200 characters)",
    )

    description: str | None = Field(
        None,
        max_length=2000,
        strip_whitespace=True,
        description="Task description (max 2000 characters)",
    )

    due_date: datetime | None = Field(None, description="Due date")

    priority: str | None = Field(
        None,
        pattern="^(low|medium|high|urgent)$",
        description="Task priority: low, medium, high, or urgent",
    )

    status: str | None = Field(
        None,
        pattern="^(todo|in_progress|review|done|cancelled)$",
        description="Task status",
    )

    assigned_to_id: UUID | None = Field(None, description="Assignee user ID")

    tags: list[str | None] = Field(None, max_items=10, description="Task tags (max 10)")

    metadata: dict | None = Field(
        None, max_length=1000, description="Additional metadata (max 1KB)"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate title content."""
        if v is None:
            return None

        if not v or not v.strip():
            raise ValueError("Title cannot be empty")

        dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
        for pattern in dangerous_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Title contains potentially unsafe content")

        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate description content."""
        if v is None:
            return None

        dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
        for pattern in dangerous_patterns:
            if pattern.lower() in v.lower():
                raise ValueError("Description contains potentially unsafe content")

        return v.strip() if v else None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str | None]) -> list[str | None]:
        """Validate tags content."""
        if v is None:
            return None

        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                continue

            tag = tag.strip()
            if tag and len(tag) <= 50:
                dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
                if not any(
                    pattern.lower() in tag.lower() for pattern in dangerous_patterns
                ):
                    validated_tags.append(tag)

        return validated_tags[:10]


class FileAttachmentSchema(BaseModel):
    """Enhanced file attachment schema with security validation."""

    file_id: UUID = Field(..., description="File ID from files module")
    file_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        strip_whitespace=True,
        description="File name",
    )

    file_size: int = Field(
        ...,
        gt=0,
        le=100 * 1024 * 1024,  # Max 100MB
        description="File size in bytes (max 100MB)",
    )

    file_type: str = Field(
        ..., pattern="^[a-zA-Z0-9/\\-_.]+$", description="File MIME type"
    )

    file_url: HttpUrl = Field(..., description="Valid file URL")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate file name for security."""
        # Check for dangerous file extensions
        dangerous_extensions = [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
            ".jar",
            ".app",
            ".deb",
            ".rpm",
            ".dmg",
            ".pkg",
            ".msi",
            ".msp",
            ".msm",
        ]

        file_lower = v.lower()
        for ext in dangerous_extensions:
            if file_lower.endswith(ext):
                raise ValueError(f"File type {ext} is not allowed")

        # Check for path traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid file name")

        return v.strip()

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        """Validate MIME type."""
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "text/csv",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ]

        if v not in allowed_types:
            raise ValueError(f"File type {v} is not allowed")

        return v
