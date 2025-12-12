"""Scheduler for time-based automation triggers."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Scheduler:
    """Scheduler for time-based rule triggers."""

    def __init__(self):
        """Initialize scheduler."""
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._scheduled_rules: dict[str, dict[str, Any]] = {}

    async def schedule_rule(
        self,
        rule_id: str,
        schedule: dict[str, Any],
        callback: Callable[[], Any],
    ) -> None:
        """Schedule a rule to be executed based on time.

        Args:
            rule_id: Rule ID
            schedule: Schedule configuration (e.g., {'type': 'interval', 'seconds': 3600})
            callback: Function to call when schedule triggers
        """
        schedule_type = schedule.get("type")

        if schedule_type == "interval":
            # Execute at regular intervals
            seconds = schedule.get("seconds", 3600)
            task = asyncio.create_task(self._interval_task(rule_id, seconds, callback))
            self._tasks.append(task)
            self._scheduled_rules[rule_id] = {"schedule": schedule, "task": task}
        elif schedule_type == "cron":
            # Execute based on cron expression (future implementation)
            logger.warning("Cron-based scheduling not yet implemented")
        elif schedule_type == "once":
            # Execute once at a specific time
            execute_at = schedule.get("execute_at")
            if execute_at:
                task = asyncio.create_task(
                    self._once_task(rule_id, execute_at, callback)
                )
                self._tasks.append(task)
                self._scheduled_rules[rule_id] = {"schedule": schedule, "task": task}
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

        logger.info(f"Scheduled rule {rule_id} with schedule type: {schedule_type}")

    async def _interval_task(
        self, rule_id: str, seconds: int, callback: Callable[[], Any]
    ) -> None:
        """Task for interval-based scheduling.

        Args:
            rule_id: Rule ID
            seconds: Interval in seconds
            callback: Function to call
        """
        while self._running:
            try:
                await asyncio.sleep(seconds)
                if self._running:
                    await callback()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled task for rule {rule_id}: {e}", exc_info=True)

    async def _once_task(
        self, rule_id: str, execute_at: str, callback: Callable[[], Any]
    ) -> None:
        """Task for one-time scheduling.

        Args:
            rule_id: Rule ID
            execute_at: ISO format datetime string
            callback: Function to call
        """
        try:
            target_time = datetime.fromisoformat(execute_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            if target_time > now:
                wait_seconds = (target_time - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                if self._running:
                    await callback()
            else:
                logger.warning(
                    f"Scheduled time {execute_at} is in the past for rule {rule_id}"
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in one-time task for rule {rule_id}: {e}", exc_info=True)

    def cancel_rule(self, rule_id: str) -> None:
        """Cancel a scheduled rule.

        Args:
            rule_id: Rule ID
        """
        if rule_id in self._scheduled_rules:
            task = self._scheduled_rules[rule_id]["task"]
            task.cancel()
            del self._scheduled_rules[rule_id]
            logger.info(f"Cancelled scheduled rule {rule_id}")

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._scheduled_rules.clear()
        logger.info("Scheduler stopped")


