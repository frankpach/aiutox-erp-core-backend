"""Automatic cache invalidation service for Tasks module."""

from uuid import UUID

from app.core.tasks.cache_service import task_cache_service


class TaskCacheInvalidationService:
    """Service for automatic cache invalidation on task operations."""

    def __init__(self):
        """Initialize cache invalidation service."""
        self.cache_service = task_cache_service

    async def invalidate_on_task_create(
        self, tenant_id: UUID, created_by_id: UUID
    ) -> None:
        """Invalidate cache when a task is created."""
        try:
            # Invalidate creator's cache
            await self.cache_service.invalidate_user_cache(tenant_id, created_by_id)

            # Invalidate any user who might see this task in their visible tasks
            # This is a broad invalidation - in production, you might want to be more specific
            await self.cache_service.invalidate_task_cache(tenant_id)
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache invalidation failed on task create: {e}")

    async def invalidate_on_task_update(
        self,
        tenant_id: UUID,
        task_id: UUID,
        old_assigned_to_id: UUID | None,
        new_assigned_to_id: UUID | None,
        created_by_id: UUID,
        updated_by_id: UUID,
    ) -> None:
        """Invalidate cache when a task is updated."""
        try:
            # Invalidate all users involved in the task
            users_to_invalidate = {created_by_id, updated_by_id}

            if old_assigned_to_id:
                users_to_invalidate.add(old_assigned_to_id)

            if new_assigned_to_id:
                users_to_invalidate.add(new_assigned_to_id)

            # Invalidate cache for each user
            for user_id in users_to_invalidate:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate specific task cache
            await self.cache_service.invalidate_task_cache(tenant_id, task_id)

        except Exception as e:
            print(f"Cache invalidation failed on task update: {e}")

    async def invalidate_on_task_delete(
        self,
        tenant_id: UUID,
        task_id: UUID,
        assigned_to_id: UUID | None,
        created_by_id: UUID,
        deleted_by_id: UUID,
    ) -> None:
        """Invalidate cache when a task is deleted."""
        try:
            # Invalidate all users involved in the task
            users_to_invalidate = {created_by_id, deleted_by_id}

            if assigned_to_id:
                users_to_invalidate.add(assigned_to_id)

            # Invalidate cache for each user
            for user_id in users_to_invalidate:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate specific task cache
            await self.cache_service.invalidate_task_cache(tenant_id, task_id)

        except Exception as e:
            print(f"Cache invalidation failed on task delete: {e}")

    async def invalidate_on_task_assign(
        self,
        tenant_id: UUID,
        task_id: UUID,
        old_assigned_to_id: UUID | None,
        new_assigned_to_id: UUID,
        assigned_by_id: UUID,
        created_by_id: UUID,
    ) -> None:
        """Invalidate cache when a task is assigned."""
        try:
            # Invalidate all users involved in the assignment
            users_to_invalidate = {created_by_id, assigned_by_id, new_assigned_to_id}

            if old_assigned_to_id:
                users_to_invalidate.add(old_assigned_to_id)

            # Invalidate cache for each user
            for user_id in users_to_invalidate:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate specific task cache
            await self.cache_service.invalidate_task_cache(tenant_id, task_id)

        except Exception as e:
            print(f"Cache invalidation failed on task assign: {e}")

    async def invalidate_on_status_change(
        self,
        tenant_id: UUID,
        task_id: UUID,
        old_status: str,
        new_status: str,
        changed_by_id: UUID,
        assigned_to_id: UUID | None,
        created_by_id: UUID,
    ) -> None:
        """Invalidate cache when task status changes."""
        try:
            # Invalidate all users involved in the status change
            users_to_invalidate = {created_by_id, changed_by_id}

            if assigned_to_id:
                users_to_invalidate.add(assigned_to_id)

            # Invalidate cache for each user
            for user_id in users_to_invalidate:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate specific task cache
            await self.cache_service.invalidate_task_cache(tenant_id, task_id)

            # Invalidate agenda cache since status changes affect calendar views
            await self.cache_service.invalidate_task_cache(tenant_id)

        except Exception as e:
            print(f"Cache invalidation failed on status change: {e}")

    async def invalidate_on_checklist_update(
        self,
        tenant_id: UUID,
        task_id: UUID,
        updated_by_id: UUID,
        assigned_to_id: UUID | None,
        created_by_id: UUID,
    ) -> None:
        """Invalidate cache when checklist is updated."""
        try:
            # Invalidate all users involved in the checklist update
            users_to_invalidate = {created_by_id, updated_by_id}

            if assigned_to_id:
                users_to_invalidate.add(assigned_to_id)

            # Invalidate cache for each user
            for user_id in users_to_invalidate:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate specific task cache
            await self.cache_service.invalidate_task_cache(tenant_id, task_id)

        except Exception as e:
            print(f"Cache invalidation failed on checklist update: {e}")

    async def invalidate_on_bulk_operations(
        self, tenant_id: UUID, user_ids: list[UUID]
    ) -> None:
        """Invalidate cache when bulk operations are performed."""
        try:
            # Invalidate cache for all affected users
            for user_id in user_ids:
                await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate all task cache for the tenant
            await self.cache_service.invalidate_task_cache(tenant_id)

        except Exception as e:
            print(f"Cache invalidation failed on bulk operations: {e}")

    async def invalidate_on_agenda_update(self, tenant_id: UUID, user_id: UUID) -> None:
        """Invalidate cache when agenda is updated."""
        try:
            # Invalidate user's agenda cache
            await self.cache_service.invalidate_user_cache(tenant_id, user_id)

            # Invalidate calendar sources cache
            await self.cache_service.invalidate_task_cache(tenant_id)

        except Exception as e:
            print(f"Cache invalidation failed on agenda update: {e}")

    async def invalidate_on_calendar_source_update(
        self, tenant_id: UUID, user_id: UUID
    ) -> None:
        """Invalidate cache when calendar sources are updated."""
        try:
            # Invalidate user's calendar sources cache
            await self.cache_service.invalidate_user_cache(tenant_id, user_id)

        except Exception as e:
            print(f"Cache invalidation failed on calendar source update: {e}")

    async def warm_up_cache(self, tenant_id: UUID, user_id: UUID) -> None:
        """Warm up cache for a user by preloading common queries."""
        try:
            # Preload common task queries

            # This would need to be called with a proper database session
            # For now, we'll just show the structure
            print(f"Warming up cache for user {user_id} in tenant {tenant_id}")

            # TODO: Preload common queries
            # - My tasks
            # - Tasks due today
            # - High priority tasks
            # - Recent tasks

        except Exception as e:
            print(f"Cache warm up failed: {e}")

    async def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        try:
            return await self.cache_service.get_cache_stats()
        except Exception as e:
            return {"available": False, "error": str(e)}


# Global cache invalidation service instance
task_cache_invalidation_service = TaskCacheInvalidationService()
