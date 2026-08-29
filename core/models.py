"""
core/models.py
~~~~~~~~~~~~~~
Domain model for ZeroForge.

Task is the central entity.  Priority and TaskStatus are string-based enums
so they serialize trivially to/from SQLite TEXT columns.

ComputedStatus represents derived task readiness — it is NEVER stored in the
database.  It is calculated at runtime from the dependency graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    """Task priority levels.  Stored as uppercase strings in SQLite."""
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

    # Numeric weight for scheduling comparisons (higher = more urgent).
    @property
    def weight(self) -> int:
        _weights = {
            Priority.LOW:      1,
            Priority.MEDIUM:   2,
            Priority.HIGH:     3,
            Priority.CRITICAL: 4,
        }
        return _weights[self]

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        try:
            return cls(value.upper())
        except ValueError:
            valid = ", ".join(p.value for p in cls)
            raise ValueError(f"Invalid priority '{value}'. Valid values: {valid}")


class TaskStatus(str, Enum):
    """
    Persistent task lifecycle states.

    READY and BLOCKED are intentionally NOT here — they are derived from
    the dependency graph and expressed via ComputedStatus.
    """
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"

    @classmethod
    def from_str(cls, value: str) -> "TaskStatus":
        try:
            return cls(value.upper())
        except ValueError:
            valid = ", ".join(s.value for s in cls)
            raise ValueError(f"Invalid status '{value}'. Valid values: {valid}")


class ComputedStatus(str, Enum):
    """
    Derived readiness state, computed from the dependency graph at runtime.
    Never stored in the database.

    READY   — task can be started immediately (all deps completed)
    BLOCKED — task cannot be started (one or more deps not completed)
    """
    READY   = "READY"
    BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    Represents a single unit of work.

    Fields
    ------
    id                : database primary key (None until persisted)
    title             : short description, required
    description       : optional longer description
    status            : current lifecycle state (persisted)
    priority          : scheduling priority (persisted)
    due_at            : optional deadline (UTC-aware datetime)
    estimated_minutes : optional effort estimate in minutes
    created_at        : UTC timestamp of creation (set automatically)
    started_at        : UTC timestamp when status changed to IN_PROGRESS
    completed_at      : UTC timestamp when status changed to COMPLETED
    """
    title             : str
    id                : Optional[int]      = field(default=None)
    description       : str                = field(default="")
    status            : TaskStatus         = field(default=TaskStatus.PENDING)
    priority          : Priority           = field(default=Priority.MEDIUM)
    due_at            : Optional[datetime] = field(default=None)
    estimated_minutes : Optional[int]      = field(default=None)
    created_at        : Optional[datetime] = field(default=None)
    started_at        : Optional[datetime] = field(default=None)
    completed_at      : Optional[datetime] = field(default=None)

    # ------------------------------------------------------------------ #
    # Convenience predicates                                               #
    # ------------------------------------------------------------------ #

    @property
    def is_done(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_active(self) -> bool:
        """True if the task can still be worked on (not completed/cancelled)."""
        return self.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)

    @property
    def is_in_progress(self) -> bool:
        return self.status == TaskStatus.IN_PROGRESS

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id}, title={self.title!r}, "
            f"status={self.status.value}, priority={self.priority.value})"
        )


# ---------------------------------------------------------------------------
# Dependency edge (lightweight — used for graph construction)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DependencyEdge:
    """
    Represents a directed dependency edge.

    Semantics: task_id depends on depends_on_id.
    In graph notation: depends_on_id → task_id.
    """
    task_id      : int
    depends_on_id: int

    def __post_init__(self) -> None:
        if self.task_id == self.depends_on_id:
            raise ValueError("A task cannot depend on itself.")
