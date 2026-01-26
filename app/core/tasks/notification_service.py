"""Task notification service integrated with existing notification system."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.logging import get_logger
from app.models.task import Task
from app.models.user import User

logger = get_logger(__name__)


class TaskNotificationService:
    """Service for managing task-related notifications."""

    def __init__(self, db=None):
        """Initialize notification service."""
        self.db = db
        # Connect to existing notification service
        try:
            from app.services.notification_service import NotificationService
            self.notification_service = NotificationService(db) if db else None
            self.is_connected = True
            logger.info("TaskNotificationService connected to NotificationService")
        except ImportError:
            logger.warning("NotificationService not found, using fallback logging")
            self.notification_service = None
            self.is_connected = False
        except Exception as e:
            logger.error(f"Failed to connect to NotificationService: {e}")
            self.notification_service = None
            self.is_connected = False

    async def notify_task_created(self, task: Task, creator: User) -> None:
        """Send notification when a task is created."""
        if task.assigned_to_id and task.assigned_to_id != creator.id:
            # Notify assigned user
            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Nueva Tarea Asignada",
                message=f"Se te ha asignado la tarea: {task.title}",
                type="task_assigned",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assigned_by": creator.full_name or creator.email,
                }
            )

        # Notify manager if task has high priority
        if task.priority == "high":
            await self._notify_managers(
                tenant_id=task.tenant_id,
                title="Tarea de Alta Prioridad Creada",
                message=f"Se ha creado una tarea de alta prioridad: {task.title}",
                type="high_priority_task",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "created_by": creator.full_name or creator.email,
                }
            )

    async def notify_task_updated(self, task: Task, updated_by: User, changes: dict) -> None:
        """Send notification when a task is updated."""
        # Notify task creator if someone else updated their task
        if task.created_by_id != updated_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Tarea Actualizada",
                message=f"Tu tarea '{task.title}' ha sido actualizada por {updated_by.full_name or updated_by.email}",
                type="task_updated",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "updated_by": updated_by.full_name or updated_by.email,
                    "changes": changes,
                }
            )

        # Notify assigned user if they're not the one who updated
        if task.assigned_to_id and task.assigned_to_id != updated_by.id and task.assigned_to_id != task.created_by_id:
            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Tarea Actualizada",
                message=f"La tarea '{task.title}' ha sido actualizada",
                type="task_updated",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "updated_by": updated_by.full_name or updated_by.email,
                    "changes": changes,
                }
            )

    async def notify_task_assigned(self, task: Task, assigned_to: User, assigned_by: User) -> None:
        """Send notification when a task is assigned to someone."""
        await self._send_notification(
            user_id=assigned_to.id,
            tenant_id=task.tenant_id,
            title="Tarea Asignada",
            message=f"Se te ha asignado la tarea: {task.title}",
            type="task_assigned",
            data={
                "task_id": str(task.id),
                "task_title": task.title,
                "assigned_by": assigned_by.full_name or assigned_by.email,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
        )

        # Notify task creator if they're not the one who assigned
        if task.created_by_id != assigned_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Tarea Reasignada",
                message=f"Tu tarea '{task.title}' ha sido asignada a {assigned_to.full_name or assigned_to.email}",
                type="task_reassigned",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assigned_to": assigned_to.full_name or assigned_to.email,
                    "assigned_by": assigned_by.full_name or assigned_by.email,
                }
            )

    async def notify_task_status_changed(self, task: Task, old_status: str, new_status: str, changed_by: User) -> None:
        """Send notification when task status changes."""
        status_messages = {
            "done": "completada",
            "in_progress": "en progreso",
            "todo": "pendiente",
            "on_hold": "en espera",
            "blocked": "bloqueada",
            "cancelled": "cancelada",
            "review": "en revisión",
        }

        status_msg = status_messages.get(new_status, new_status)

        # Notify task creator
        if task.created_by_id != changed_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Estado de Tarea Cambiado",
                message=f"La tarea '{task.title}' ahora está {status_msg}",
                type="task_status_changed",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by": changed_by.full_name or changed_by.email,
                }
            )

        # Notify assigned user if different from creator and changer
        if (task.assigned_to_id and
            task.assigned_to_id != changed_by.id and
            task.assigned_to_id != task.created_by_id):

            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Estado de Tarea Cambiado",
                message=f"La tarea '{task.title}' ahora está {status_msg}",
                type="task_status_changed",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by": changed_by.full_name or changed_by.email,
                }
            )

        # Special notifications for important status changes
        if new_status == "done":
            await self._notify_task_completed(task, changed_by)
        elif new_status == "overdue":
            await self._notify_task_overdue(task)

    async def notify_task_completed(self, task: Task, completed_by: User) -> None:
        """Send notification when a task is completed."""
        # Notify task creator
        if task.created_by_id != completed_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="¡Tarea Completada!",
                message=f"La tarea '{task.title}' ha sido completada por {completed_by.full_name or completed_by.email}",
                type="task_completed",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "completed_by": completed_by.full_name or completed_by.email,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )

        # Notify managers for high priority tasks
        if task.priority == "high":
            await self._notify_managers(
                tenant_id=task.tenant_id,
                title="Tarea de Alta Prioridad Completada",
                message=f"La tarea de alta prioridad '{task.title}' ha sido completada",
                type="high_priority_task_completed",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "completed_by": completed_by.full_name or completed_by.email,
                }
            )

    async def notify_task_due_soon(self, task: Task) -> None:
        """Send notification when a task is due soon."""
        if not task.due_date:
            return

        # Check if due within 24 hours
        now = datetime.now(UTC)
        if task.due_date <= now + timedelta(hours=24) and task.due_date > now:
            hours_until_due = int((task.due_date - now).total_seconds() / 3600)

            # Notify assigned user
            if task.assigned_to_id:
                await self._send_notification(
                    user_id=task.assigned_to_id,
                    tenant_id=task.tenant_id,
                    title="Tarea Próxima a Vencer",
                    message=f"La tarea '{task.title}' vence en {hours_until_due} horas",
                    type="task_due_soon",
                    data={
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "due_date": task.due_date.isoformat(),
                        "hours_until_due": hours_until_due,
                    }
                )

            # Notify task creator
            if task.created_by_id != task.assigned_to_id:
                await self._send_notification(
                    user_id=task.created_by_id,
                    tenant_id=task.tenant_id,
                    title="Tarea Próxima a Vencer",
                    message=f"La tarea '{task.title}' vence en {hours_until_due} horas",
                    type="task_due_soon",
                    data={
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "due_date": task.due_date.isoformat(),
                        "hours_until_due": hours_until_due,
                    }
                )

    async def notify_task_overdue(self, task: Task) -> None:
        """Send notification when a task is overdue."""
        if not task.due_date or task.due_date > datetime.now(UTC):
            return

        # Notify assigned user
        if task.assigned_to_id:
            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Tarea Vencida",
                message=f"La tarea '{task.title}' está vencida",
                type="task_overdue",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "due_date": task.due_date.isoformat(),
                    "days_overdue": (datetime.now(UTC) - task.due_date).days,
                }
            )

        # Notify task creator
        if task.created_by_id != task.assigned_to_id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Tarea Vencida",
                message=f"La tarea '{task.title}' está vencida",
                type="task_overdue",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "due_date": task.due_date.isoformat(),
                    "days_overdue": (datetime.now(UTC) - task.due_date).days,
                }
            )

    async def notify_task_unassigned(self, task: Task, unassigned_user: User, unassigned_by: User) -> None:
        """Send notification when a task is unassigned from someone."""
        await self._send_notification(
            user_id=unassigned_user.id,
            tenant_id=task.tenant_id,
            title="Tarea Desasignada",
            message=f"Se te ha desasignado la tarea: {task.title}",
            type="task_unassigned",
            data={
                "task_id": str(task.id),
                "task_title": task.title,
                "unassigned_by": unassigned_by.full_name or unassigned_by.email,
            }
        )

        # Notify task creator if they're not the one who unassigned
        if task.created_by_id != unassigned_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Tarea Desasignada",
                message=f"La tarea '{task.title}' ha sido desasignada de {unassigned_user.full_name or unassigned_user.email}",
                type="task_unassigned",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "unassigned_user": unassigned_user.full_name or unassigned_user.email,
                    "unassigned_by": unassigned_by.full_name or unassigned_by.email,
                }
            )

    async def notify_comment_added(self, task: Task, comment_text: str, commented_by: User) -> None:
        """Send notification when a comment is added to a task."""
        # Notify task creator if they're not the one who commented
        if task.created_by_id != commented_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Nuevo Comentario en Tarea",
                message=f"{commented_by.full_name or commented_by.email} comentó en '{task.title}': {comment_text[:100]}",
                type="task_comment_added",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "comment_text": comment_text,
                    "commented_by": commented_by.full_name or commented_by.email,
                }
            )

        # Notify assigned user if different from creator and commenter
        if (task.assigned_to_id and
            task.assigned_to_id != commented_by.id and
            task.assigned_to_id != task.created_by_id):
            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Nuevo Comentario en Tarea",
                message=f"{commented_by.full_name or commented_by.email} comentó en '{task.title}': {comment_text[:100]}",
                type="task_comment_added",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "comment_text": comment_text,
                    "commented_by": commented_by.full_name or commented_by.email,
                }
            )

    async def notify_file_attached(self, task: Task, filename: str, attached_by: User) -> None:
        """Send notification when a file is attached to a task."""
        # Notify task creator if they're not the one who attached
        if task.created_by_id != attached_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Archivo Adjuntado a Tarea",
                message=f"{attached_by.full_name or attached_by.email} adjuntó '{filename}' a la tarea '{task.title}'",
                type="task_file_attached",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "filename": filename,
                    "attached_by": attached_by.full_name or attached_by.email,
                }
            )

        # Notify assigned user if different from creator and attacher
        if (task.assigned_to_id and
            task.assigned_to_id != attached_by.id and
            task.assigned_to_id != task.created_by_id):
            await self._send_notification(
                user_id=task.assigned_to_id,
                tenant_id=task.tenant_id,
                title="Archivo Adjuntado a Tarea",
                message=f"{attached_by.full_name or attached_by.email} adjuntó '{filename}' a la tarea '{task.title}'",
                type="task_file_attached",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "filename": filename,
                    "attached_by": attached_by.full_name or attached_by.email,
                }
            )

    async def notify_checklist_updated(self, task: Task, updated_by: User, item_text: str, completed: bool) -> None:
        """Send notification when checklist item is updated."""
        action = "completado" if completed else "marcado como pendiente"

        # Notify task creator if they're not the one who updated
        if task.created_by_id != updated_by.id:
            await self._send_notification(
                user_id=task.created_by_id,
                tenant_id=task.tenant_id,
                title="Checklist Actualizado",
                message=f"Item '{item_text}' {action} en la tarea '{task.title}'",
                type="checklist_updated",
                data={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "item_text": item_text,
                    "completed": completed,
                    "updated_by": updated_by.full_name or updated_by.email,
                }
            )

    async def _send_notification(
        self,
        user_id: UUID,
        tenant_id: UUID,
        title: str,
        message: str,
        type: str,
        data: dict,
    ) -> None:
        """Send notification through the existing notification system."""
        try:
            if self.is_connected and self.notification_service:
                # Use real notification service
                await self.notification_service.create_notification(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    title=title,
                    message=message,
                    type=type,
                    data=data,
                    channels=["in_app", "email"],  # Configurable channels
                    priority="normal"  # Based on task priority
                )
                logger.info(f"Notification sent via NotificationService: {title}")
            else:
                # Fallback: Simulate the notification service call
                notification_data = {
                    "user_id": str(user_id),
                    "tenant_id": str(tenant_id),
                    "title": title,
                    "message": message,
                    "type": type,
                    "data": data,
                    "channels": ["in_app", "email"],
                    "priority": "normal",
                    "created_at": datetime.now(UTC).isoformat()
                }

                # Log the notification (simulating the real service)
                logger.info(f"NOTIFICATION_SENT (fallback): {notification_data}")

        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Failed to send notification: {e}")
            # Continue without failing the main operation

    async def _notify_managers(
        self,
        tenant_id: UUID,
        title: str,
        message: str,
        type: str,
        data: dict,
    ) -> None:
        """Notify all managers in the tenant."""
        # This would get all managers from the user service
        # For now, we'll create a mock implementation
        try:
            # TODO: Get managers from user service and send notifications
            # managers = user_service.get_managers(tenant_id)
            # for manager in managers:
            #     await self._send_notification(
            #         user_id=manager.id,
            #         tenant_id=tenant_id,
            #         title=title,
            #         message=message,
            #         type=type,
            #         data=data,
            #     )
            print(f"Manager notification for tenant {tenant_id}: {title}")
        except Exception as e:
            print(f"Failed to notify managers: {e}")

    async def notify_tasks_due_soon(self, tasks: list[Task], window: str) -> None:
        """Send notifications for multiple tasks due soon.

        Args:
            tasks: List of tasks due soon
            window: Time window (24h, 1h, 15min)
        """
        for task in tasks:
            try:
                await self.notify_task_due_soon(task)
                logger.info(f"Sent due_soon notification for task {task.id} ({window})")
            except Exception as e:
                logger.error(f"Failed to send due_soon notification for task {task.id}: {e}")

    async def notify_tasks_overdue(self, tasks: list[Task]) -> None:
        """Send notifications for multiple overdue tasks.

        Args:
            tasks: List of overdue tasks
        """
        for task in tasks:
            try:
                await self.notify_task_overdue(task)
                logger.info(f"Sent overdue notification for task {task.id}")
            except Exception as e:
                logger.error(f"Failed to send overdue notification for task {task.id}: {e}")

    async def check_and_send_due_notifications(self, tenant_id: UUID) -> None:
        """Check for tasks due soon and send notifications."""
        # This would be called by a scheduled job
        try:
            # TODO: Get tasks due soon from repository
            # tasks = task_repository.get_tasks_due_soon(tenant_id)
            # for task in tasks:
            #     await self.notify_task_due_soon(task)
            print(f"Checked due notifications for tenant {tenant_id}")
        except Exception as e:
            print(f"Failed to check due notifications: {e}")


# Global notification service instance factory
def get_task_notification_service(db=None) -> TaskNotificationService:
    """Get TaskNotificationService instance."""
    return TaskNotificationService(db)

# Global instance for backward compatibility
task_notification_service = TaskNotificationService()
