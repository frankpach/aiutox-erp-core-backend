"""
Topics estándar del sistema pub/sub.

Convención de nombres: {modulo}.{entidad}.{accion}
"""

# ============================================
# TASKS
# ============================================
TASK_CREATED = "tasks.created"
TASK_UPDATED = "tasks.updated"
TASK_DELETED = "tasks.deleted"
TASK_ASSIGNED = "tasks.assigned"
TASK_STATUS_CHANGED = "tasks.status_changed"
TASK_COMPLETED = "tasks.completed"
TASK_MOVED = "tasks.moved"

# Task Dependencies
TASK_DEPENDENCY_CREATED = "task_dependency.created"
TASK_DEPENDENCY_REMOVED = "task_dependency.removed"

# Task Statuses
TASK_STATUS_CREATED = "task_status.created"
TASK_STATUS_UPDATED = "task_status.updated"
TASK_STATUS_DELETED = "task_status.deleted"

# Task Templates
TASK_TEMPLATE_CREATED = "task_template.created"
TASK_TEMPLATE_UPDATED = "task_template.updated"
TASK_TEMPLATE_DELETED = "task_template.deleted"

# ============================================
# CALENDAR
# ============================================
CALENDAR_EVENT_CREATED = "calendar.event.created"
CALENDAR_EVENT_UPDATED = "calendar.event.updated"
CALENDAR_EVENT_DELETED = "calendar.event.deleted"
CALENDAR_SHARED = "calendar.shared"
CALENDAR_UNSHARED = "calendar.unshared"

# Recurrences
CALENDAR_RECURRENCE_CREATED = "calendar.recurrence.created"
CALENDAR_RECURRENCE_EXCEPTION = "calendar.recurrence.exception"

# Resources
CALENDAR_RESOURCE_CREATED = "calendar.resource.created"
CALENDAR_RESOURCE_RESERVED = "calendar.resource.reserved"
CALENDAR_RESOURCE_RELEASED = "calendar.resource.released"

# ============================================
# APPROVALS
# ============================================
APPROVAL_CREATED = "approvals.created"
APPROVAL_STATUS_CHANGED = "approvals.status_changed"
APPROVAL_APPROVED = "approvals.approved"
APPROVAL_REJECTED = "approvals.rejected"

# ============================================
# WORKFLOWS
# ============================================
WORKFLOW_STARTED = "workflows.started"
WORKFLOW_STEP_COMPLETED = "workflows.step_completed"
WORKFLOW_COMPLETED = "workflows.completed"
WORKFLOW_FAILED = "workflows.failed"

# ============================================
# NOTIFICATIONS
# ============================================
NOTIFICATION_SEND = "notifications.send"
NOTIFICATION_READ = "notifications.read"
NOTIFICATION_DELETED = "notifications.deleted"

# ============================================
# FILES
# ============================================
FILE_UPLOADED = "files.uploaded"
FILE_SHARED = "files.shared"
FILE_DELETED = "files.deleted"

# ============================================
# TEAMS
# ============================================
TEAM_MEMBER_ADDED = "teams.member_added"
TEAM_MEMBER_REMOVED = "teams.member_removed"
TEAM_MEMBER_ROLE_CHANGED = "teams.member_role_changed"

# ============================================
# SCHEDULER
# ============================================
SCHEDULER_EVENT_SCHEDULED = "scheduler.event_scheduled"
SCHEDULER_EVENT_CANCELLED = "scheduler.event_cancelled"
SCHEDULER_RESOURCE_CONFLICT = "scheduler.resource_conflict"

# ============================================
# AUTOMATION
# ============================================
AUTOMATION_TRIGGERED = "automation.triggered"
AUTOMATION_EXECUTED = "automation.executed"
AUTOMATION_FAILED = "automation.failed"
