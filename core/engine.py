"""
core/engine.py
~~~~~~~~~~~~~~
Central orchestrator for ZeroForge.

The Engine is the single entry point between the CLI and the rest of the
system.  The CLI calls engine methods; the engine coordinates validators,
database, dependency graph, and scheduler.

The CLI must NEVER call the database directly.
The engine must NEVER parse CLI arguments directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.dependency import DependencyGraph
from core.models import Task, TaskStatus, Priority, ComputedStatus
from core.scheduler import generate_plan, full_execution_order
from core.validator import (
    validate_title,
    validate_priority,
    validate_status,
    validate_estimated_minutes,
    validate_due_date,
    validate_description,
)
from storage.database import Database
from utils.dates import now_utc, format_display, to_storage_str
from utils.errors import (
    DependencyCycleError,
    DependencyError,
    InvalidTaskError,
    TaskNotFoundError,
)
from utils.formatting import render_graph_ascii


class Engine:
    """
    Coordinates all ZeroForge business operations.

    Parameters
    ----------
    db : an initialised Database instance
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Task lifecycle                                                       #
    # ------------------------------------------------------------------ #

    def add_task(
        self,
        title: str,
        *,
        priority: str = "MEDIUM",
        description: str = "",
        due_at: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        after: Optional[List[int]] = None,
    ) -> Task:
        """
        Create a new task and optionally add dependency edges.

        Parameters
        ----------
        title              : task title (required)
        priority           : priority string (default MEDIUM)
        description        : optional description
        due_at             : optional deadline string (YYYY-MM-DD)
        estimated_minutes  : optional effort estimate
        after              : list of task IDs this task depends on

        Returns the newly created Task.
        """
        # Validate inputs.
        title       = validate_title(title)
        prio        = validate_priority(priority)
        desc        = validate_description(description)
        due_dt      = validate_due_date(due_at) if due_at else None
        est_mins    = validate_estimated_minutes(estimated_minutes) if estimated_minutes else None

        # Validate dependency IDs exist before creating the task.
        after_ids: List[int] = after or []
        for dep_id in after_ids:
            if not self._db.task_exists(dep_id):
                raise TaskNotFoundError(dep_id)

        # Build and persist the task.
        task = Task(
            title             = title,
            description       = desc,
            status            = TaskStatus.PENDING,
            priority          = prio,
            due_at            = due_dt,
            estimated_minutes = est_mins,
            created_at        = now_utc(),
        )
        task_id = self._db.create_task(task)
        task.id = task_id

        # Add dependency edges.
        # Cycle check: task is brand new so it can't yet form a cycle,
        # but if after_ids themselves are circular among each other (they
        # would already have been rejected when they were added), we're safe.
        for dep_id in after_ids:
            # Self-dependency can't happen (task just created ≠ dep_id)
            edges = self._db.all_edges()
            edges.append((task_id, dep_id))
            graph = DependencyGraph(edges)
            cycle = graph.find_cycle()
            if cycle:
                # Roll back the edge (don't add it).
                raise DependencyCycleError(cycle)
            self._db.add_dependency(task_id, dep_id)

        return self._db.get_task(task_id)

    def get_task(self, task_id: int) -> Task:
        """Retrieve a task by ID.  Raises TaskNotFoundError if missing."""
        return self._db.get_task(task_id)

    def list_tasks(self, status_filter: Optional[str] = None) -> List[Task]:
        """
        Return all tasks, optionally filtered by status string.
        """
        if status_filter:
            status_filter = validate_status(status_filter).value
        return self._db.list_tasks(status_filter)

    def update_task(
        self,
        task_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_at: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        clear_due: bool = False,
    ) -> Task:
        """
        Update one or more fields of an existing task.

        Only fields that are explicitly provided are changed.
        Pass clear_due=True to remove the deadline.
        """
        # Ensure task exists.
        self._db.get_task(task_id)

        updates: Dict = {}
        if title is not None:
            updates["title"] = validate_title(title)
        if description is not None:
            updates["description"] = validate_description(description)
        if priority is not None:
            updates["priority"] = validate_priority(priority).value
        if due_at is not None:
            updates["due_at"] = to_storage_str(validate_due_date(due_at))
        if clear_due:
            updates["due_at"] = None
        if estimated_minutes is not None:
            updates["estimated_minutes"] = validate_estimated_minutes(estimated_minutes)

        if updates:
            self._db.update_task(task_id, **updates)

        return self._db.get_task(task_id)

    def delete_task(self, task_id: int) -> None:
        """
        Delete a task.

        All dependency edges involving this task are cascade-deleted.
        """
        self._db.get_task(task_id)  # raises TaskNotFoundError if missing
        self._db.delete_task(task_id)

    def start_task(self, task_id: int) -> Task:
        """
        Transition a task to IN_PROGRESS.

        Rejected if:
        - Task is already completed or cancelled.
        - Task is BLOCKED (not all dependencies completed).
        """
        task = self._db.get_task(task_id)

        if task.status == TaskStatus.COMPLETED:
            raise InvalidTaskError(f"Task #{task_id} is already completed.")
        if task.status == TaskStatus.CANCELLED:
            raise InvalidTaskError(f"Task #{task_id} is cancelled and cannot be started.")
        if task.status == TaskStatus.IN_PROGRESS:
            raise InvalidTaskError(f"Task #{task_id} is already in progress.")

        # Check readiness.
        computed = self._compute_single_status(task_id)
        if computed == "BLOCKED":
            blocking = self._db.get_dependencies(task_id)
            blocking_ids = [d for d in blocking if not self._db.get_task(d).is_done]
            ids_str = ", ".join(f"#{i}" for i in blocking_ids)
            raise InvalidTaskError(
                f"Task #{task_id} is blocked by: {ids_str}. "
                f"Complete those tasks first."
            )

        self._db.update_task(task_id, status=TaskStatus.IN_PROGRESS, started_at=now_utc())
        return self._db.get_task(task_id)

    def complete_task(self, task_id: int) -> Task:
        """
        Mark a task as COMPLETED.

        Rejected if the task is already completed or cancelled.
        """
        task = self._db.get_task(task_id)

        if task.status == TaskStatus.COMPLETED:
            raise InvalidTaskError(f"Task #{task_id} is already completed.")
        if task.status == TaskStatus.CANCELLED:
            raise InvalidTaskError(f"Task #{task_id} is cancelled.")

        self._db.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            completed_at=now_utc(),
        )
        return self._db.get_task(task_id)

    def cancel_task(self, task_id: int) -> Task:
        """
        Cancel a task.

        Cancelled tasks remain in the database but are excluded from scheduling.
        """
        task = self._db.get_task(task_id)

        if task.status == TaskStatus.COMPLETED:
            raise InvalidTaskError(
                f"Task #{task_id} is completed and cannot be cancelled. "
                f"Use 'delete' if you want to remove it."
            )
        if task.status == TaskStatus.CANCELLED:
            raise InvalidTaskError(f"Task #{task_id} is already cancelled.")

        self._db.update_task(task_id, status=TaskStatus.CANCELLED)
        return self._db.get_task(task_id)

    # ------------------------------------------------------------------ #
    # Dependency management                                                #
    # ------------------------------------------------------------------ #

    def add_dependency(self, task_id: int, depends_on_id: int) -> None:
        """
        Add a dependency: task_id will depend on depends_on_id.

        Validates:
        - Both tasks exist.
        - Not a self-dependency.
        - No duplicate.
        - No cycle would be created.
        """
        if task_id == depends_on_id:
            raise DependencyError(f"Task #{task_id} cannot depend on itself.")

        self._db.get_task(task_id)       # raises if not found
        self._db.get_task(depends_on_id) # raises if not found

        # Check for duplicate.
        existing = self._db.get_dependencies(task_id)
        if depends_on_id in existing:
            raise DependencyError(
                f"Task #{task_id} already depends on #{depends_on_id}."
            )

        # Cycle check: build graph with the proposed edge and look for cycles.
        edges = self._db.all_edges()
        edges.append((task_id, depends_on_id))
        graph = DependencyGraph(edges)
        cycle = graph.find_cycle()
        if cycle:
            raise DependencyCycleError(cycle)

        self._db.add_dependency(task_id, depends_on_id)

    def remove_dependency(self, task_id: int, depends_on_id: int) -> None:
        """
        Remove a dependency edge.

        Raises DependencyError if the edge does not exist.
        """
        self._db.get_task(task_id)
        self._db.get_task(depends_on_id)

        removed = self._db.remove_dependency(task_id, depends_on_id)
        if not removed:
            raise DependencyError(
                f"No dependency exists: #{task_id} → #{depends_on_id}."
            )

    def list_dependencies(self, task_id: int) -> Dict[str, List[int]]:
        """
        Return the dependency relationships for a task.

        Returns:
            {
              "depends_on": [ids this task depends on],
              "dependents": [ids that depend on this task],
            }
        """
        self._db.get_task(task_id)
        return {
            "depends_on": self._db.get_dependencies(task_id),
            "dependents": self._db.get_dependents(task_id),
        }

    # ------------------------------------------------------------------ #
    # Status queries                                                       #
    # ------------------------------------------------------------------ #

    def ready_tasks(self) -> List[Task]:
        """Return READY tasks ranked by scheduling priority."""
        all_tasks = self._db.list_tasks()
        edges = self._db.all_edges()
        return generate_plan(all_tasks, edges)

    def blocked_tasks(self) -> List[Tuple[Task, List[int]]]:
        """
        Return blocked tasks with the IDs of the tasks blocking them.

        Returns list of (task, blocking_dep_ids).
        """
        all_tasks = self._db.list_tasks()
        edges = self._db.all_edges()

        completed_ids: Set[int] = {
            t.id for t in all_tasks
            if t.status == TaskStatus.COMPLETED and t.id is not None
        }
        active = [
            t for t in all_tasks
            if t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
            and t.id is not None
        ]

        graph = DependencyGraph(edges)
        active_ids: Set[int] = {t.id for t in active}  # type: ignore[misc]
        status_map = graph.compute_status(active_ids, completed_ids)

        result = []
        for task in active:
            if status_map.get(task.id) == "BLOCKED":
                blockers = graph.blocking_tasks(task.id, completed_ids)
                result.append((task, blockers))

        return result

    def generate_plan(self) -> List[Task]:
        """Generate a full execution plan including all active tasks in wave order."""
        all_tasks = self._db.list_tasks()
        edges = self._db.all_edges()
        return full_execution_order(all_tasks, edges)

    def get_graph_data(self) -> Dict:
        """
        Return data needed to render the dependency graph.

        Returns:
            {
              "tasks":     {id: title},
              "edges":     [(task_id, depends_on_id), ...],
              "topo_order": [ids in topological order],
            }
        """
        all_tasks = self._db.list_tasks()
        edges = self._db.all_edges()

        task_dict = {t.id: t.title for t in all_tasks if t.id is not None}

        if not task_dict:
            return {"tasks": {}, "edges": [], "topo_order": []}

        graph = DependencyGraph(edges)
        cycle = graph.find_cycle()
        if cycle:
            raise DependencyCycleError(cycle)

        # Include all task IDs in topological sort.
        all_ids = set(task_dict.keys())
        # Add any IDs referenced in edges but missing from task list.
        for (tid, dep) in edges:
            all_ids.add(tid)
            all_ids.add(dep)

        topo = graph.topological_order(include_ids=all_ids)

        return {
            "tasks": task_dict,
            "edges": edges,
            "topo_order": topo,
        }

    def get_computed_status(self, task_id: int) -> str:
        """
        Return 'READY' or 'BLOCKED' for a single task.

        Returns the stored status string for COMPLETED / CANCELLED tasks.
        """
        task = self._db.get_task(task_id)
        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return task.status.value
        if task.status == TaskStatus.IN_PROGRESS:
            return "IN_PROGRESS"
        return self._compute_single_status(task_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _compute_single_status(self, task_id: int) -> str:
        """Compute READY/BLOCKED for a single task using the full graph."""
        all_tasks = self._db.list_tasks()
        edges = self._db.all_edges()
        completed_ids: Set[int] = {
            t.id for t in all_tasks
            if t.status == TaskStatus.COMPLETED and t.id is not None
        }
        graph = DependencyGraph(edges)
        result = graph.compute_status({task_id}, completed_ids)
        return result.get(task_id, "READY")

    def show_task(self, task_id: int) -> Dict:
        """
        Return a rich task view with computed status and dependencies.

        Returns:
            {
              "task":           Task,
              "computed_status": "READY" | "BLOCKED" | "IN_PROGRESS" | ...,
              "depends_on":     [Task, ...],
              "dependents":     [Task, ...],
            }
        """
        task = self._db.get_task(task_id)
        computed = self.get_computed_status(task_id)

        dep_ids = self._db.get_dependencies(task_id)
        dependent_ids = self._db.get_dependents(task_id)

        depends_on_tasks = [self._db.get_task(d) for d in dep_ids]
        dependent_tasks  = [self._db.get_task(d) for d in dependent_ids]

        return {
            "task":            task,
            "computed_status": computed,
            "depends_on":      depends_on_tasks,
            "dependents":      dependent_tasks,
        }
