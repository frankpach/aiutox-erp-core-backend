"""Calendar models for calendar and event management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class CalendarType(str, Enum):
    """Types of calendars."""

    USER = "user"
    ORGANIZATION = "organization"
    SHARED = "shared"


class EventStatus(str, Enum):
    """Event status."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AttendeeStatus(str, Enum):
    """Attendee response status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"


class RecurrenceType(str, Enum):
    """Recurrence types for events."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ReminderType(str, Enum):
    """Reminder types."""

    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"


class Calendar(Base):
    """Calendar model for organizing events."""

    __tablename__ = "calendars"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calendar information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    calendar_type = Column(String(20), nullable=False, default=CalendarType.USER)

    # Ownership
    owner_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Organization (if organization calendar)
    organization_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Settings
    is_public = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Metadata
    meta_data = Column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_calendars_tenant_owner", "tenant_id", "owner_id"),
        Index("idx_calendars_organization", "tenant_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<Calendar(id={self.id}, name={self.name}, type={self.calendar_type})>"


class CalendarEvent(Base):
    """Calendar event model."""

    __tablename__ = "calendar_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calendar relationship
    calendar_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)

    # Time information
    start_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), nullable=True)  # e.g., "America/New_York"
    all_day = Column(Boolean, default=False, nullable=False)

    # Status
    status = Column(String(20), nullable=False, default=EventStatus.SCHEDULED, index=True)

    # Recurrence (simple fields for backward compatibility)
    recurrence_type = Column(String(20), nullable=False, default=RecurrenceType.NONE)
    recurrence_end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    recurrence_count = Column(Integer, nullable=True)  # Number of occurrences
    recurrence_interval = Column(Integer, default=1, nullable=False)  # Every N days/weeks/months
    recurrence_days_of_week = Column(String(20), nullable=True)  # e.g., "1,3,5" for Mon,Wed,Fri
    recurrence_day_of_month = Column(Integer, nullable=True)  # For monthly recurrence
    recurrence_month_of_year = Column(Integer, nullable=True)  # For yearly recurrence

    # Advanced recurrence (RFC5545 RRULE)
    recurrence_rule = Column(Text, nullable=True)  # RRULE string (e.g., "FREQ=WEEKLY;BYDAY=MO,WE,FR")
    recurrence_exdates = Column(JSONB, nullable=True)  # Array of exception dates

    # Unified source (for event aggregation)
    source_type = Column(String(50), nullable=True, index=True)  # 'task', 'approval', 'workflow', 'external'
    source_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)  # ID of source entity

    # External integration
    provider = Column(String(50), nullable=True, index=True)  # 'google', 'outlook', 'ical', 'caldav'
    external_id = Column(String(255), nullable=True, index=True)  # External event ID
    read_only = Column(Boolean, default=False, nullable=False)  # If event is read-only (from external source)

    # Organizer
    organizer_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    meta_data = Column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    calendar = relationship("Calendar", back_populates="events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")
    reminders = relationship("EventReminder", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_events_calendar_time", "calendar_id", "start_time"),
        Index("idx_events_tenant_time", "tenant_id", "start_time", "end_time"),
        Index("idx_events_status", "tenant_id", "status"),
        Index("idx_events_source", "source_type", "source_id"),
        Index("idx_events_external", "provider", "external_id"),
    )

    def __repr__(self) -> str:
        return f"<CalendarEvent(id={self.id}, title={self.title}, start={self.start_time})>"


class EventAttendee(Base):
    """Event attendee model."""

    __tablename__ = "event_attendees"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event relationship
    event_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendar_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Attendee information
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email = Column(String(255), nullable=True)  # For external attendees
    name = Column(String(255), nullable=True)  # For external attendees

    # Response
    status = Column(String(20), nullable=False, default=AttendeeStatus.PENDING, index=True)
    response_at = Column(TIMESTAMP(timezone=True), nullable=True)
    comment = Column(Text, nullable=True)  # Optional comment with response

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    event = relationship("CalendarEvent", back_populates="attendees")

    __table_args__ = (
        Index("idx_attendees_event_user", "event_id", "user_id"),
        Index("idx_attendees_status", "event_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<EventAttendee(id={self.id}, event_id={self.event_id}, status={self.status})>"


class EventReminder(Base):
    """Event reminder model."""

    __tablename__ = "event_reminders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event relationship
    event_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendar_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reminder information
    reminder_type = Column(String(20), nullable=False)  # email, in_app, push
    minutes_before = Column(Integer, nullable=False)  # Minutes before event start
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)  # When reminder was sent
    is_sent = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    event = relationship("CalendarEvent", back_populates="reminders")

    __table_args__ = (Index("idx_reminders_event_sent", "event_id", "is_sent"),)

    def __repr__(self) -> str:
        return f"<EventReminder(id={self.id}, event_id={self.event_id}, minutes={self.minutes_before})>"


class ResourceType(str, Enum):
    """Resource types for scheduler."""

    ROOM = "room"
    EQUIPMENT = "equipment"
    USER = "user"


class CalendarResource(Base):
    """Calendar resource model for scheduler view."""

    __tablename__ = "calendar_resources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Calendar relationship (optional - resource can be shared across calendars)
    calendar_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendars.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Resource information
    name = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)  # room, equipment, user
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code

    # Capacity and availability
    capacity = Column(Integer, nullable=True)  # For rooms/equipment
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    meta_data = Column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    event_resources = relationship("EventResource", back_populates="resource", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_resources_tenant_type", "tenant_id", "resource_type"),
    )

    def __repr__(self) -> str:
        return f"<CalendarResource(id={self.id}, name={self.name}, type={self.resource_type})>"


class EventResource(Base):
    """Event-Resource junction table (many-to-many)."""

    __tablename__ = "event_resources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event relationship
    event_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendar_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Resource relationship
    resource_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("calendar_resources.id", ondelete="CASCADE"),
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
    event = relationship("CalendarEvent")
    resource = relationship("CalendarResource", back_populates="event_resources")

    __table_args__ = (
        Index("idx_event_resources_unique", "event_id", "resource_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<EventResource(event_id={self.event_id}, resource_id={self.resource_id})>"








