"""Calendar schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Calendar schemas
class CalendarBase(BaseModel):
    """Base schema for calendar."""

    name: str = Field(..., description="Calendar name", max_length=255)
    description: str | None = Field(None, description="Calendar description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    calendar_type: str = Field(..., description="Calendar type (user, organization, shared)")
    organization_id: UUID | None = Field(None, description="Organization ID (for organization calendars)")
    is_public: bool = Field(False, description="Whether calendar is public")
    is_default: bool = Field(False, description="Whether this is the default calendar")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarCreate(CalendarBase):
    """Schema for creating a calendar."""

    pass


class CalendarUpdate(BaseModel):
    """Schema for updating a calendar."""

    name: str | None = Field(None, description="Calendar name", max_length=255)
    description: str | None = Field(None, description="Calendar description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    is_public: bool | None = Field(None, description="Whether calendar is public")
    is_default: bool | None = Field(None, description="Whether this is the default calendar")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarResponse(CalendarBase):
    """Schema for calendar response."""

    id: UUID
    tenant_id: UUID
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Event schemas
class CalendarEventBase(BaseModel):
    """Base schema for calendar event."""

    calendar_id: UUID = Field(..., description="Calendar ID")
    title: str = Field(..., description="Event title", max_length=255)
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location", max_length=500)
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    timezone: str | None = Field(None, description="Timezone (e.g., 'America/New_York')", max_length=50)
    all_day: bool = Field(False, description="Whether event is all-day")
    status: str = Field("scheduled", description="Event status")

    # Simple recurrence fields (backward compatibility)
    recurrence_type: str = Field("none", description="Recurrence type (none, daily, weekly, monthly, yearly)")
    recurrence_end_date: datetime | None = Field(None, description="Recurrence end date")
    recurrence_count: int | None = Field(None, description="Number of occurrences")
    recurrence_interval: int = Field(1, description="Recurrence interval (every N days/weeks/months)")
    recurrence_days_of_week: str | None = Field(None, description="Days of week for recurrence (e.g., '1,3,5')")
    recurrence_day_of_month: int | None = Field(None, description="Day of month for monthly recurrence")
    recurrence_month_of_year: int | None = Field(None, description="Month of year for yearly recurrence")

    # Advanced recurrence (RFC5545 RRULE)
    recurrence_rule: str | None = Field(None, description="RRULE string (e.g., 'FREQ=WEEKLY;BYDAY=MO,WE,FR')")
    recurrence_exdates: list[str] | None = Field(None, description="Array of exception dates (ISO format)")

    # Unified source fields
    source_type: str | None = Field(None, description="Source type (task, approval, workflow, external)")
    source_id: UUID | None = Field(None, description="Source entity ID")

    # External integration fields
    provider: str | None = Field(None, description="External provider (google, outlook, ical, caldav)")
    external_id: str | None = Field(None, description="External event ID")
    read_only: bool = Field(False, description="Whether event is read-only")

    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarEventCreate(CalendarEventBase):
    """Schema for creating a calendar event."""

    pass


class CalendarEventUpdate(BaseModel):
    """Schema for updating a calendar event."""

    title: str | None = Field(None, description="Event title", max_length=255)
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location", max_length=500)
    start_time: datetime | None = Field(None, description="Event start time")
    end_time: datetime | None = Field(None, description="Event end time")
    timezone: str | None = Field(None, description="Timezone", max_length=50)
    all_day: bool | None = Field(None, description="Whether event is all-day")
    status: str | None = Field(None, description="Event status")

    # Simple recurrence fields
    recurrence_type: str | None = Field(None, description="Recurrence type")
    recurrence_end_date: datetime | None = Field(None, description="Recurrence end date")
    recurrence_count: int | None = Field(None, description="Number of occurrences")
    recurrence_interval: int | None = Field(None, description="Recurrence interval")
    recurrence_days_of_week: str | None = Field(None, description="Days of week for recurrence")
    recurrence_day_of_month: int | None = Field(None, description="Day of month for monthly recurrence")
    recurrence_month_of_year: int | None = Field(None, description="Month of year for yearly recurrence")

    # Advanced recurrence
    recurrence_rule: str | None = Field(None, description="RRULE string")
    recurrence_exdates: list[str] | None = Field(None, description="Array of exception dates")

    # Unified source fields (usually not updated manually)
    source_type: str | None = Field(None, description="Source type")
    source_id: UUID | None = Field(None, description="Source entity ID")

    # External integration fields (usually not updated manually)
    provider: str | None = Field(None, description="External provider")
    external_id: str | None = Field(None, description="External event ID")
    read_only: bool | None = Field(None, description="Whether event is read-only")

    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarEventResponse(CalendarEventBase):
    """Schema for calendar event response."""

    id: UUID
    tenant_id: UUID
    organizer_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Attendee schemas
class EventAttendeeBase(BaseModel):
    """Base schema for event attendee."""

    event_id: UUID = Field(..., description="Event ID")
    user_id: UUID | None = Field(None, description="User ID (for internal attendees)")
    email: str | None = Field(None, description="Email (for external attendees)", max_length=255)
    name: str | None = Field(None, description="Name (for external attendees)", max_length=255)
    status: str = Field("pending", description="Attendee status (pending, accepted, declined, tentative)")
    comment: str | None = Field(None, description="Optional comment with response")


class EventAttendeeCreate(EventAttendeeBase):
    """Schema for creating an event attendee."""

    pass


class EventAttendeeUpdate(BaseModel):
    """Schema for updating an event attendee."""

    status: str | None = Field(None, description="Attendee status")
    comment: str | None = Field(None, description="Optional comment with response")


class EventAttendeeResponse(EventAttendeeBase):
    """Schema for event attendee response."""

    id: UUID
    tenant_id: UUID
    response_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Reminder schemas
class EventReminderBase(BaseModel):
    """Base schema for event reminder."""

    event_id: UUID = Field(..., description="Event ID")
    reminder_type: str = Field(..., description="Reminder type (email, in_app, push)")
    minutes_before: int = Field(..., description="Minutes before event start")


class EventReminderCreate(EventReminderBase):
    """Schema for creating an event reminder."""

    @field_validator('reminder_type')
    @classmethod
    def validate_reminder_type(cls, v):
        """Validate reminder type."""
        valid_types = ['email', 'in_app', 'push']
        if v not in valid_types:
            raise ValueError(f'Reminder type must be one of: {", ".join(valid_types)}')
        return v

    @field_validator('minutes_before')
    @classmethod
    def validate_minutes_before(cls, v):
        """Validate minutes before event."""
        if v < 0:
            raise ValueError('Minutes before must be non-negative')
        if v > 525600:  # Maximum 1 year in minutes
            raise ValueError('Minutes before cannot exceed 525600 (1 year)')
        return v

    @model_validator(mode='before')
    @classmethod
    def validate_reminder_logic(cls, data):
        """Validate reminder logic constraints."""
        if isinstance(data, dict):
            # Additional business logic validations can be added here
            # For example, limit number of reminders per event type
            pass
        return data


class EventReminderResponse(EventReminderBase):
    """Schema for event reminder response."""

    id: UUID
    tenant_id: UUID
    sent_at: datetime | None
    is_sent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Resource schemas
class CalendarResourceBase(BaseModel):
    """Base schema for calendar resource."""

    calendar_id: UUID | None = Field(None, description="Calendar ID (optional, can be shared)")
    name: str = Field(..., description="Resource name", max_length=255)
    resource_type: str = Field(..., description="Resource type (room, equipment, user)")
    description: str | None = Field(None, description="Resource description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    capacity: int | None = Field(None, description="Capacity (for rooms/equipment)")
    is_active: bool = Field(True, description="Whether resource is active")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarResourceCreate(CalendarResourceBase):
    """Schema for creating a calendar resource."""

    pass


class CalendarResourceUpdate(BaseModel):
    """Schema for updating a calendar resource."""

    name: str | None = Field(None, description="Resource name", max_length=255)
    resource_type: str | None = Field(None, description="Resource type")
    description: str | None = Field(None, description="Resource description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    capacity: int | None = Field(None, description="Capacity")
    is_active: bool | None = Field(None, description="Whether resource is active")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarResourceResponse(CalendarResourceBase):
    """Schema for calendar resource response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Event-Resource junction schemas
class EventResourceCreate(BaseModel):
    """Schema for assigning a resource to an event."""

    resource_id: UUID = Field(..., description="Resource ID")


class EventResourceResponse(BaseModel):
    """Schema for event-resource assignment response."""

    id: UUID
    tenant_id: UUID
    event_id: UUID
    resource_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)





