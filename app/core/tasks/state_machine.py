"""Task state machine for validating state transitions."""

from typing import Dict, List, Set
from enum import Enum

from app.models.task import TaskStatus


class TaskTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted."""

    def __init__(self, from_state: str, to_state: str, allowed_states: List[str]):
        self.from_state = from_state
        self.to_state = to_state
        self.allowed_states = allowed_states
        message = f"Invalid transition from '{from_state}' to '{to_state}'. Allowed states: {', '.join(allowed_states)}"
        super().__init__(message)


class TaskStateMachine:
    """State machine for managing task status transitions."""

    # Define valid transitions
    VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
        TaskStatus.TODO: {
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.ON_HOLD,
            TaskStatus.CANCELLED,
        },
        TaskStatus.IN_PROGRESS: {
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
            TaskStatus.ON_HOLD,
            TaskStatus.REVIEW,
            TaskStatus.CANCELLED,
        },
        TaskStatus.ON_HOLD: {
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.CANCELLED,
        },
        TaskStatus.BLOCKED: {
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.CANCELLED,
        },
        TaskStatus.REVIEW: {
            TaskStatus.DONE,
            TaskStatus.BLOCKED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.CANCELLED,
        },
        TaskStatus.DONE: {
            TaskStatus.TODO,  # Allow reopening tasks
            TaskStatus.IN_PROGRESS,  # Allow reopening for rework
        },
        TaskStatus.CANCELLED: {
            TaskStatus.TODO,  # Allow reactivating cancelled tasks
            TaskStatus.IN_PROGRESS,
        },
    }

    # Define business rules for specific transitions
    TRANSITION_RULES = {
        # Rules that require specific conditions
        (TaskStatus.TODO, TaskStatus.DONE): {
            "error": "Cannot mark task as done directly. Must be in progress first.",
            "allowed": False,
        },
        (TaskStatus.TODO, TaskStatus.REVIEW): {
            "error": "Cannot send task to review directly. Must be in progress first.",
            "allowed": False,
        },
        (TaskStatus.DONE, TaskStatus.CANCELLED): {
            "error": "Cannot cancel a completed task. Reopen it first.",
            "allowed": False,
        },
        (TaskStatus.CANCELLED, TaskStatus.DONE): {
            "error": "Cannot mark cancelled task as done directly. Reactivate it first.",
            "allowed": False,
        },
    }

    @classmethod
    def validate_transition(cls, from_state: TaskStatus, to_state: TaskStatus) -> bool:
        """
        Validate if a state transition is allowed.

        Args:
            from_state: Current task status
            to_state: Target task status

        Returns:
            True if transition is valid, False otherwise

        Raises:
            TaskTransitionError: If transition is invalid with details
        """
        # Check if it's the same state (no transition)
        if from_state == to_state:
            return True

        # Check specific business rules
        rule = cls.TRANSITION_RULES.get((from_state, to_state))
        if rule and not rule.get("allowed", True):
            raise TaskTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
                allowed_states=[],
            )

        # Check if transition is in valid transitions
        allowed_states = cls.VALID_TRANSITIONS.get(from_state, set())

        if to_state not in allowed_states:
            allowed_state_names = [state.value for state in allowed_states]
            raise TaskTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
                allowed_states=allowed_state_names,
            )

        return True

    @classmethod
    def get_allowed_transitions(cls, from_state: TaskStatus) -> List[TaskStatus]:
        """
        Get all allowed transitions from a given state.

        Args:
            from_state: Current task status

        Returns:
            List of allowed target states
        """
        return list(cls.VALID_TRANSITIONS.get(from_state, set()))

    @classmethod
    def get_transition_path(cls, from_state: TaskStatus, to_state: TaskStatus) -> List[TaskStatus]:
        """
        Get the shortest path from one state to another.

        Args:
            from_state: Starting state
            to_state: Target state

        Returns:
            List of states representing the path, or empty list if no path exists
        """
        if from_state == to_state:
            return [from_state]

        # Simple BFS to find shortest path
        from collections import deque

        queue = deque([(from_state, [from_state])])
        visited = {from_state}

        while queue:
            current_state, path = queue.popleft()

            # Check if we reached the target
            if current_state == to_state:
                return path

            # Explore neighbors
            for next_state in cls.VALID_TRANSITIONS.get(current_state, set()):
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        return []  # No path found

    @classmethod
    def can_reach_state(cls, from_state: TaskStatus, to_state: TaskStatus) -> bool:
        """
        Check if a state can be reached from another state (directly or indirectly).

        Args:
            from_state: Starting state
            to_state: Target state

        Returns:
            True if reachable, False otherwise
        """
        return len(cls.get_transition_path(from_state, to_state)) > 0

    @classmethod
    def get_state_metadata(cls, state: TaskStatus) -> Dict[str, any]:
        """
        Get metadata about a state (color, icon, description, etc.).

        Args:
            state: Task status

        Returns:
            Dictionary with state metadata
        """
        metadata = {
            TaskStatus.TODO: {
                "color": "gray",
                "icon": "circle",
                "description": "Task not started",
                "category": "pending",
            },
            TaskStatus.IN_PROGRESS: {
                "color": "blue",
                "icon": "play-circle",
                "description": "Task in progress",
                "category": "active",
            },
            TaskStatus.ON_HOLD: {
                "color": "yellow",
                "icon": "pause-circle",
                "description": "Task paused",
                "category": "pending",
            },
            TaskStatus.BLOCKED: {
                "color": "red",
                "icon": "stop-circle",
                "description": "Task blocked",
                "category": "blocked",
            },
            TaskStatus.REVIEW: {
                "color": "purple",
                "icon": "eye",
                "description": "Task under review",
                "category": "active",
            },
            TaskStatus.DONE: {
                "color": "green",
                "icon": "check-circle",
                "description": "Task completed",
                "category": "completed",
            },
            TaskStatus.CANCELLED: {
                "color": "gray",
                "icon": "x-circle",
                "description": "Task cancelled",
                "category": "completed",
            },
        }

        return metadata.get(state, {
            "color": "gray",
            "icon": "help-circle",
            "description": "Unknown state",
            "category": "unknown",
        })

    @classmethod
    def get_states_by_category(cls, category: str) -> List[TaskStatus]:
        """
        Get all states in a specific category.

        Args:
            category: Category name (pending, active, blocked, completed)

        Returns:
            List of states in the category
        """
        return [
            state for state in TaskStatus
            if cls.get_state_metadata(state)["category"] == category
        ]
