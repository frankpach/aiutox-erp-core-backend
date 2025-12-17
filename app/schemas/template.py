"""Template schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Template schemas
class TemplateBase(BaseModel):
    """Base schema for template."""

    name: str = Field(..., description="Template name", max_length=255)
    description: str | None = Field(None, description="Template description")
    template_type: str = Field(..., description="Template type (document, email, sms, notification)", max_length=20)
    template_format: str = Field(..., description="Template format (html, pdf, text, markdown)", max_length=20)
    category: str | None = Field(None, description="Template category", max_length=50)
    content: str = Field(..., description="Template content")
    variables: dict[str, Any] | None = Field(None, description="Available variables and their types")
    is_active: bool = Field(True, description="Whether template is active")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""

    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    name: str | None = Field(None, description="Template name", max_length=255)
    description: str | None = Field(None, description="Template description")
    category: str | None = Field(None, description="Template category", max_length=50)
    content: str | None = Field(None, description="Template content")
    variables: dict[str, Any] | None = Field(None, description="Available variables")
    is_active: bool | None = Field(None, description="Whether template is active")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TemplateResponse(TemplateBase):
    """Schema for template response."""

    id: UUID
    tenant_id: UUID
    is_system: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Template Version schemas
class TemplateVersionBase(BaseModel):
    """Base schema for template version."""

    template_id: UUID = Field(..., description="Template ID")
    version_number: int = Field(..., description="Version number")
    content: str = Field(..., description="Template content for this version")
    variables: dict[str, Any] | None = Field(None, description="Variables for this version")
    changelog: str | None = Field(None, description="What changed in this version")
    is_current: bool = Field(True, description="Whether this is the current version")


class TemplateVersionCreate(TemplateVersionBase):
    """Schema for creating a template version."""

    pass


class TemplateVersionResponse(TemplateVersionBase):
    """Schema for template version response."""

    id: UUID
    tenant_id: UUID
    created_by: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Template Render schemas
class TemplateRenderRequest(BaseModel):
    """Schema for rendering a template."""

    template_id: UUID = Field(..., description="Template ID")
    variables: dict[str, Any] = Field(..., description="Variables to render template with")
    format: str | None = Field(None, description="Output format (if different from template format)")


class TemplateRenderResponse(BaseModel):
    """Schema for template render response."""

    rendered_content: str = Field(..., description="Rendered template content")
    format: str = Field(..., description="Output format")
    variables_used: dict[str, Any] = Field(..., description="Variables used in rendering")


# Template Category schemas
class TemplateCategoryBase(BaseModel):
    """Base schema for template category."""

    name: str = Field(..., description="Category name", max_length=100)
    description: str | None = Field(None, description="Category description")
    parent_id: UUID | None = Field(None, description="Parent category ID")
    is_active: bool = Field(True, description="Whether category is active")


class TemplateCategoryCreate(TemplateCategoryBase):
    """Schema for creating a template category."""

    pass


class TemplateCategoryResponse(TemplateCategoryBase):
    """Schema for template category response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)







