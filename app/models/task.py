"""Task models for task and workflow management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base
# Import TaskStatus and TaskTemplate models to ensure they're available for relationships
from app.models.task_status import TaskStatus  # noqa: F401
from app.models.task_template import TaskTemplate  # noqa: F401


class TaskStatusEnum(str, Enum):
    """Task status enumeration."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """Task model for task management."""

    __tablename__ = "tasks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Task information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=TaskStatusEnum.TODO, index=True)
    priority = Column(String(20), nullable=False, default=TaskPriority.MEDIUM, index=True)

    # Assignment (legacy field for backward compatibility, use TaskAssignment for multiple)
    assigned_to_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Dates
    due_date = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    start_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    end_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    all_day = Column(Boolean, default=False, nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Multi-module integration (standard payload)
    source_module = Column(String(50), nullable=True, index=True)  # e.g., 'projects', 'workflows'
    source_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)  # ID of source entity
    source_context = Column(JSONB, nullable=True)  # Additional context from source module

    # Polymorphic relationship (legacy, kept for backward compatibility)
    related_entity_type = Column(String(50), nullable=True, index=True)  # e.g., 'product', 'order'
    related_entity_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Workflow reference (optional)
    workflow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workflow_step_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Board view and templates (Fase 1)
    status_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("task_statuses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    board_order = Column(Integer, nullable=True)
    template_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("task_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    task_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata as JSON
    tags = Column(JSONB, nullable=True)  # Array of tag names or IDs
    tag_ids = Column(JSONB, nullable=True)  # Array of tag UUIDs for core tags
    color_override = Column(String(7), nullable=True)  # Hex color override

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

    # Relationships
    parent_task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subtasks = relationship("Task", back_populates="parent_task")
    parent_task = relationship("Task", back_populates="subtasks", remote_side=[id])
    assignments = relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")
    checklist_items = relationship("TaskChecklistItem", back_populates="task", cascade="all, delete-orphan")
    status_obj = relationship("TaskStatus", back_populates="tasks", foreign_keys=[status_id])
    template = relationship("TaskTemplate", back_populates="tasks")

    __table_args__ = (
        Index("idx_tasks_tenant_status", "tenant_id", "status"),
        Index("idx_tasks_tenant_priority", "tenant_id", "priority"),
        Index("idx_tasks_assigned", "tenant_id", "assigned_to_id"),
        Index("idx_tasks_due_date", "tenant_id", "due_date"),
        Index("idx_tasks_tenant_start_at", "tenant_id", "start_at"),
        Index("idx_tasks_tenant_end_at", "tenant_id", "end_at"),
        Index("idx_tasks_entity", "related_entity_type", "related_entity_id"),
        Index("idx_tasks_source", "source_module", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


TaskStatus = TaskStatusEnum


class TaskChecklistItem(Base):
    """Task checklist item model."""

    __tablename__ = "task_checklist_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Checklist item information
    title = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False, nullable=False, index=True)
    order = Column(Integer, default=0, nullable=False)

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
    task = relationship("Task", back_populates="checklist_items")

    __table_args__ = (
        Index("idx_task_checklist_task", "task_id", "order"),
    )

    def __repr__(self) -> str:
        return f"<TaskChecklistItem(id={self.id}, task_id={self.task_id}, title={self.title})>"


class TaskAssignment(Base):
    """Task assignment model for multi-user and multi-team assignments."""

    __tablename__ = "task_assignments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assignment target (user or team)
    assigned_to_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    assigned_to_group_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Assignment metadata
    assigned_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=True)  # e.g., 'owner', 'reviewer', 'contributor'
    notes = Column(Text, nullable=True)

    # Auditoría completa
    created_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    updated_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    # Relationships
    task = relationship("Task", back_populates="assignments")

    __table_args__ = (
        Index("idx_task_assignments_task", "tenant_id", "task_id"),
        Index("idx_task_assignments_user", "tenant_id", "assigned_to_id"),
        Index("idx_task_assignments_group", "tenant_id", "assigned_to_group_id"),
        # Constraint: Al menos uno debe estar presente
        CheckConstraint(
            "(assigned_to_id IS NOT NULL) OR (assigned_to_group_id IS NOT NULL)",
            name="check_assignment_target"
        ),
        # Constraint: Solo uno puede estar presente
        CheckConstraint(
            "(assigned_to_id IS NULL) OR (assigned_to_group_id IS NULL)",
            name="check_assignment_exclusive"
        ),
    )

    def __repr__(self) -> str:
        return f"<TaskAssignment(id={self.id}, task_id={self.task_id}, assigned_to_id={self.assigned_to_id})>"


class Workflow(Base):
    """Workflow model for configurable workflows."""

    __tablename__ = "workflows"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Workflow information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Workflow definition (BPMN-ready structure)
    definition = Column(JSONB, nullable=False)  # Workflow definition as JSON

    # Metadata
    workflow_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata

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
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_workflows_tenant_enabled", "tenant_id", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name={self.name}, enabled={self.enabled})>"


class WorkflowStep(Base):
    """Workflow step model for workflow steps."""

    __tablename__ = "workflow_steps"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Step information
    name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)  # e.g., 'task', 'approval', 'condition'
    order = Column(Integer, nullable=False)

    # Step configuration
    config = Column(JSONB, nullable=True)  # Step-specific configuration

    # Transitions (next steps)
    transitions = Column(JSONB, nullable=True)  # Array of transition configs

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
    workflow = relationship("Workflow", back_populates="steps")

    __table_args__ = (
        Index("idx_workflow_steps_workflow", "workflow_id", "order"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowStep(id={self.id}, workflow_id={self.workflow_id}, name={self.name})>"


class WorkflowExecution(Base):
    """Workflow execution model for tracking workflow runs."""

    __tablename__ = "workflow_executions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Execution information
    status = Column(String(20), nullable=False, default="running", index=True)  # running, completed, failed, cancelled
    current_step_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_steps.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Context (polymorphic relationship)
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Execution data
    execution_data = Column(JSONB, nullable=True)  # Data passed through workflow
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")

    __table_args__ = (
        Index("idx_workflow_executions_workflow", "workflow_id", "status"),
        Index("idx_workflow_executions_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"


class TaskReminderType(str, Enum):
    """Task reminder type enumeration."""

    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class TaskReminder(Base):
    """Task reminder model for task reminders."""

    __tablename__ = "task_reminders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reminder information
    reminder_type = Column(String(50), nullable=False, default=TaskReminderType.IN_APP)
    reminder_time = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    message = Column(Text, nullable=True)

    # Status
    sent = Column(Boolean, default=False, nullable=False, index=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

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
    task = relationship("Task", backref="reminders")

    __table_args__ = (
        Index("idx_task_reminders_task", "task_id", "reminder_time"),
        Index("idx_task_reminders_tenant", "tenant_id", "reminder_time"),
        Index("idx_task_reminders_pending", "tenant_id", "sent", "reminder_time"),
    )

    def __repr__(self) -> str:
        return f"<TaskReminder(id={self.id}, task_id={self.task_id}, reminder_time={self.reminder_time})>"


class TaskRecurrenceFrequency(str, Enum):
    """Task recurrence frequency enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class TaskRecurrence(Base):
    """Task recurrence model for recurring tasks."""

    __tablename__ = "task_recurrences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Recurrence configuration
    frequency = Column(String(50), nullable=False, default=TaskRecurrenceFrequency.WEEKLY)
    interval = Column(Integer, nullable=False, default=1)  # e.g., every 2 weeks

    # Date configuration
    start_date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True, index=True)

    # Occurrence limits
    max_occurrences = Column(Integer, nullable=True)
    current_occurrence = Column(Integer, nullable=False, default=1)

    # Days of week for weekly recurrence (JSON array: [0,1,2,3,4,5,6] where 0=Monday)
    days_of_week = Column(JSONB, nullable=True)

    # Day of month for monthly recurrence (1-31)
    day_of_month = Column(Integer, nullable=True)

    # Custom recurrence configuration (cron-like or custom rules)
    custom_config = Column(JSONB, nullable=True)

    # Status
    active = Column(Boolean, default=True, nullable=False, index=True)

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
    task = relationship("Task", backref="recurrence")

    __table_args__ = (
        Index("idx_task_recurrences_task", "task_id", "active"),
        Index("idx_task_recurrences_tenant", "tenant_id", "active"),
        Index("idx_task_recurrences_dates", "tenant_id", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return f"<TaskRecurrence(id={self.id}, task_id={self.task_id}, frequency={self.frequency})>"
