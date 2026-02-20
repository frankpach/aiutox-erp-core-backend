"""Autodiscovery system for webhook events from active modules."""

import importlib
import logging
from collections.abc import Callable

from app.core.integrations.event_registry import (
    ModuleEventRegistry,
    get_event_registry,
)
from app.core.module_registry import ModuleRegistry

logger = logging.getLogger(__name__)


def discover_and_register_events() -> None:
    """Discover and register webhook events from all active modules.

    This function:
    1. Reads the module configuration to find active modules
    2. Attempts to import each module's events.py file
    3. Calls the get_*_events() function to retrieve event definitions
    4. Registers events in the global event registry
    """
    registry = get_event_registry()
    module_registry = ModuleRegistry()

    # Map of module names to their event getter functions
    module_event_getters: dict[str, tuple[str, str]] = {
        "tasks": ("app.core.tasks.events", "get_task_events"),
        "files": ("app.core.files.events", "get_file_events"),
        "templates": ("app.core.templates.events", "get_template_events"),
        "search": ("app.core.search.events", "get_search_events"),
        "notifications": ("app.core.notifications.events", "get_notification_events"),
        "import_export": ("app.core.import_export.events", "get_import_export_events"),
    }

    for module_name, (module_path, getter_name) in module_event_getters.items():
        # Check if module is enabled in config
        if not module_registry.is_module_enabled(module_name):
            logger.debug(
                f"Module '{module_name}' is disabled, skipping event registration"
            )
            continue

        try:
            # Import the module's events file
            events_module = importlib.import_module(module_path)

            # Get the event getter function
            getter_func: Callable[[], ModuleEventRegistry] = getattr(
                events_module, getter_name
            )

            # Call the getter to get the module's event registry
            module_event_registry = getter_func()

            # Register the module's events
            registry.register_module(module_event_registry)

            logger.info(
                f"Registered {len(module_event_registry.events)} events from module '{module_name}'"
            )

        except ImportError as e:
            logger.warning(f"Could not import events for module '{module_name}': {e}")
        except AttributeError as e:
            logger.warning(
                f"Module '{module_name}' does not have getter function '{getter_name}': {e}"
            )
        except Exception as e:
            logger.error(
                f"Error registering events for module '{module_name}': {e}",
                exc_info=True,
            )


def get_available_events() -> dict[str, dict]:
    """Get all available webhook events from active modules.

    Returns:
        Dictionary of modules and their events
    """
    registry = get_event_registry()
    return registry.get_all_events()


def get_all_event_types() -> list[str]:
    """Get list of all event types across all modules.

    Returns:
        List of event type strings
    """
    registry = get_event_registry()
    return registry.get_event_types()
