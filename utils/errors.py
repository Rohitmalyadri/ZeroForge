"""
utils/errors.py
~~~~~~~~~~~~~~~
Custom exception hierarchy for ZeroForge.

All public exceptions inherit from ZeroForgeError so callers can catch
the entire family with a single except clause when needed.
"""


class ZeroForgeError(Exception):
    """Base exception for all ZeroForge errors."""


class TaskNotFoundError(ZeroForgeError):
    """Raised when a task ID does not exist in the database."""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Task #{task_id} not found.")


class InvalidTaskError(ZeroForgeError):
    """Raised when task data fails validation."""


class DependencyError(ZeroForgeError):
    """Raised for invalid dependency operations."""


class DependencyCycleError(DependencyError):
    """Raised when adding a dependency would create a cycle."""

    def __init__(self, cycle: list) -> None:
        self.cycle = cycle
        cycle_str = " -> ".join(f"#{n}" for n in cycle)
        super().__init__(f"Dependency cycle detected: {cycle_str}")


class InvalidDateError(ZeroForgeError):
    """Raised when a date string cannot be parsed."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(
            f"Invalid date '{value}'. Expected format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS"
        )


class StorageError(ZeroForgeError):
    """Raised when a database operation fails unexpectedly."""
