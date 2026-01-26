"""Task module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_task_events() -> ModuleEventRegistry:
    """Get task module webhook events.

    Returns:
        ModuleEventRegistry with all task events
    """
    return ModuleEventRegistry(
        module_name="tasks",
        display_name="Tareas",
        description="Eventos del módulo de gestión de tareas",
        events=[
            # Lifecycle events
            WebhookEvent(
                type="task.created",
                description="Tarea creada",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="task.updated",
                description="Tarea actualizada",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="task.deleted",
                description="Tarea eliminada",
                category=EventCategory.LIFECYCLE,
            ),
            # Status events
            WebhookEvent(
                type="task.status_changed",
                description="Estado de tarea cambiado",
                category=EventCategory.STATUS,
            ),
            WebhookEvent(
                type="task.completed",
                description="Tarea completada",
                category=EventCategory.STATUS,
            ),
            WebhookEvent(
                type="task.cancelled",
                description="Tarea cancelada",
                category=EventCategory.STATUS,
            ),
            # Interaction events
            WebhookEvent(
                type="task.assigned",
                description="Tarea asignada a usuario",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.unassigned",
                description="Tarea desasignada",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.comment_added",
                description="Comentario agregado a tarea",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.comment_updated",
                description="Comentario actualizado",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.comment_deleted",
                description="Comentario eliminado",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.user_mentioned",
                description="Usuario mencionado en comentario",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.file_attached",
                description="Archivo adjuntado a tarea",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="task.file_removed",
                description="Archivo removido de tarea",
                category=EventCategory.INTERACTION,
            ),
            # System events
            WebhookEvent(
                type="task.due_soon",
                description="Tarea próxima a vencer",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="task.overdue",
                description="Tarea vencida",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="task.calendar_synced",
                description="Tarea sincronizada con calendario",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="task.calendar_unsynced",
                description="Tarea desincronizada de calendario",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="task.calendar_updated",
                description="Evento de calendario actualizado",
                category=EventCategory.SYSTEM,
            ),
        ],
    )
