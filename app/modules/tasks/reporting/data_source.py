"""Data source for tasks statistics and reporting."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.reporting.data_source import BaseDataSource
from app.models.task import Task, TaskPriority, TaskStatusEnum
from app.models.task_status import TaskStatus


class TasksDataSource(BaseDataSource):
    """Data source para estadísticas de tareas."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize data source with database session and tenant ID."""
        super().__init__(db, tenant_id)

    async def get_data(
        self, filters: dict[str, Any] | None = None, pagination: dict[str, int] | None = None
    ) -> dict[str, Any]:
        """Obtiene datos de tareas según filtros."""
        filters = filters or {}
        pagination = pagination or {}

        # Build base query with tenant filtering
        query = self.db.query(Task).filter(Task.tenant_id == self.tenant_id)

        # Apply filters
        if "status" in filters:
            query = query.filter(Task.status == filters["status"])

        if "priority" in filters:
            query = query.filter(Task.priority == filters["priority"])

        if "assigned_to" in filters:
            query = query.filter(Task.assigned_to_id == filters["assigned_to"])

        if "date_from" in filters:
            query = query.filter(Task.created_at >= filters["date_from"])

        if "date_to" in filters:
            query = query.filter(Task.created_at <= filters["date_to"])

        # Get total count
        total = query.count()

        # Apply pagination
        skip = pagination.get("skip", 0)
        limit = pagination.get("limit", 100)
        query = query.offset(skip).limit(limit)

        # Execute query
        tasks = query.all()

        # Convert to dict format
        data = []
        for task in tasks:
            data.append({
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "tenant_id": str(task.tenant_id)
            })

        return {"data": data, "total": total}

    def get_statistics(self, filters: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        """Estadísticas generales."""
        # Build base query with tenant filtering
        base_query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Apply date filters if present
        if "date_from" in filters:
            base_query = base_query.filter(Task.created_at >= filters["date_from"])
        if "date_to" in filters:
            base_query = base_query.filter(Task.created_at <= filters["date_to"])

        # Total tasks
        total_tasks = base_query.count()

        # Tasks by status
        status_counts = (
            base_query.with_entities(Task.status, func.count(Task.id))
            .group_by(Task.status)
            .all()
        )
        by_status = {status: count for status, count in status_counts}

        # Tasks by priority
        priority_counts = (
            base_query.with_entities(Task.priority, func.count(Task.id))
            .group_by(Task.priority)
            .all()
        )
        by_priority = {priority: count for priority, count in priority_counts}

        # Tasks by custom state (using TaskStatus table)
        custom_state_counts = (
            self.db.query(TaskStatus.name, func.count(Task.id))
            .join(Task, Task.status_id == TaskStatus.id)
            .filter(TaskStatus.tenant_id == tenant_id, not TaskStatus.is_system)
            .group_by(TaskStatus.name)
            .all()
        )
        by_custom_state = {state: count for state, count in custom_state_counts}

        # Completion metrics
        completed_tasks = base_query.filter(Task.status == TaskStatusEnum.DONE).count()
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Overdue tasks
        overdue_tasks = base_query.filter(
            and_(
                Task.due_date < datetime.utcnow(),
                Task.status.notin_([TaskStatusEnum.DONE, TaskStatusEnum.CANCELLED])
            )
        ).count()

        return {
            "total_tasks": total_tasks,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_custom_state": by_custom_state,
            "completion_rate": round(completion_rate, 2),
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks
        }

    def get_trends(self, period: str, tenant_id: str) -> dict[str, Any]:
        """Tendencias temporales."""
        # Determine date range based on period
        now = datetime.now(UTC)
        if period == "7d":
            start_date = now - timedelta(days=7)
            interval = "day"
        elif period == "30d":
            start_date = now - timedelta(days=30)
            interval = "day"
        elif period == "90d":
            start_date = now - timedelta(days=90)
            interval = "week"
        else:  # default to 30 days
            start_date = now - timedelta(days=30)
            interval = "day"

        # Query tasks created over time
        if interval == "day":
            date_trunc = func.date_trunc("day", Task.created_at)
        else:  # week
            date_trunc = func.date_trunc("week", Task.created_at)

        created_trends = (
            self.db.query(date_trunc.label("period"), func.count(Task.id).label("count"))
            .filter(Task.tenant_id == tenant_id, Task.created_at >= start_date)
            .group_by(date_trunc)
            .order_by(date_trunc)
            .all()
        )

        # Query tasks completed over time
        completed_trends = (
            self.db.query(date_trunc.label("period"), func.count(Task.id).label("count"))
            .filter(
                Task.tenant_id == tenant_id,
                Task.completed_at >= start_date,
                Task.completed_at.is_not(None)
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
            .all()
        )

        # Format data points
        data_points = []
        created_dict = {str(period): count for period, count in created_trends}
        completed_dict = {str(period): count for period, count in completed_trends}

        # Combine dates from both trends
        all_dates = set(created_dict.keys()) | set(completed_dict.keys())
        for date_str in sorted(all_dates):
            data_points.append({
                "period": date_str,
                "created": created_dict.get(date_str, 0),
                "completed": completed_dict.get(date_str, 0)
            })

        return {
            "period": period,
            "data_points": data_points
        }

    def get_custom_states_metrics(self, tenant_id: str) -> list[dict[str, Any]]:
        """Métricas de estados custom."""
        # Query custom states and their metrics
        metrics = (
            self.db.query(
                TaskStatus.id,
                TaskStatus.name,
                TaskStatus.type,
                TaskStatus.color,
                func.count(Task.id).label("task_count"),
                func.avg(
                    func.extract(
                        "epoch",
                        func.coalesce(Task.completed_at, datetime.now(UTC)) - Task.created_at
                    )
                ).label("avg_time_seconds")
            )
            .join(Task, Task.status_id == TaskStatus.id, isouter=True)
            .filter(TaskStatus.tenant_id == tenant_id, not TaskStatus.is_system)
            .group_by(TaskStatus.id, TaskStatus.name, TaskStatus.type, TaskStatus.color)
            .all()
        )

        result = []
        for metric in metrics:
            avg_time_hours = None
            if metric.avg_time_seconds:
                avg_time_hours = round(float(metric.avg_time_seconds) / 3600, 2)

            result.append({
                "state_id": str(metric.id),
                "state_name": metric.name,
                "state_type": metric.type,
                "state_color": metric.color,
                "task_count": metric.task_count,
                "avg_time_in_state_hours": avg_time_hours
            })

        return result

    def get_columns(self) -> list[dict[str, Any]]:
        """Get available columns for this data source."""
        return [
            {"name": "id", "type": "uuid", "label": "ID"},
            {"name": "title", "type": "string", "label": "Title"},
            {"name": "status", "type": "string", "label": "Status"},
            {"name": "priority", "type": "string", "label": "Priority"},
            {"name": "assigned_to_id", "type": "uuid", "label": "Assigned To"},
            {"name": "created_at", "type": "datetime", "label": "Created At"},
            {"name": "due_date", "type": "datetime", "label": "Due Date"},
            {"name": "completed_at", "type": "datetime", "label": "Completed At"},
            {"name": "tenant_id", "type": "uuid", "label": "Tenant ID"}
        ]

    def get_filters(self) -> list[dict[str, Any]]:
        """Get available filters for this data source."""
        return [
            {
                "name": "status",
                "type": "select",
                "label": "Status",
                "options": [
                    {"value": status.value, "label": status.value}
                    for status in TaskStatusEnum
                ]
            },
            {
                "name": "priority",
                "type": "select",
                "label": "Priority",
                "options": [
                    {"value": priority.value, "label": priority.value}
                    for priority in TaskPriority
                ]
            },
            {
                "name": "assigned_to",
                "type": "select",
                "label": "Assigned To",
                "options": []  # Would need to query users
            },
            {
                "name": "date_from",
                "type": "date",
                "label": "Date From"
            },
            {
                "name": "date_to",
                "type": "date",
                "label": "Date To"
            }
        ]
