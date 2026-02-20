"""Preference inheritance logic (org -> role -> user)."""

from typing import Any


def merge_preferences(
    org_prefs: dict[str, Any],
    role_prefs: dict[str, Any],
    user_prefs: dict[str, Any],
) -> dict[str, Any]:
    """Merge preferences with inheritance order: org -> role -> user.

    User preferences override role preferences, which override org preferences.

    Args:
        org_prefs: Organization preferences dictionary
        role_prefs: Role preferences dictionary
        user_prefs: User preferences dictionary

    Returns:
        Merged preferences dictionary
    """
    # Start with org preferences
    merged = org_prefs.copy()

    # Override with role preferences
    merged.update(role_prefs)

    # Override with user preferences (highest priority)
    merged.update(user_prefs)

    return merged
