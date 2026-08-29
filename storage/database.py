"""
storage/database.py
~~~~~~~~~~~~~~~~~~~
SQLite persistence layer for ZeroForge.

Design principles:
- All SQL uses parameterized queries (no string concatenation).
- Foreign key enforcement is enabled on every connection.
- WAL journal mode for better concurrent read performance.
- Storage layer returns/accepts domain objects (Task) not raw tuples.
- Deleting a task cascades to dependency edges (ON DELETE CASCADE).
- Transactions are used for multi-statement operations.

This module knows about SQL and sqlite3.  It does NOT know about business
rules — those live in core/engine.py.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from core.models import Task, TaskStatus, Priority
from storage.migrations import apply_migrations
from utils.dates import from_storage_str, to_storage_str
from utils.errors import StorageError, TaskNotFoundError


# ---------------------------------------------------------------------------
# Row → Task conversion
# ---------------------------------------------------------------------------

def _row_to_task(row: sqlite3.Row) -> Task:
    """Convert a sqlite3.Row into a Task domain object."""
    def _parse_dt(val: Optional[str]) -> Optional[datetime]:
        return from_storage_str(val) if val else None

    return Task(
        id                = row["id"],
        title             = row["title"],
        description       = row["description"] or "",
        status            = TaskStatus(row["status"]),
        priority          = Priority(row["priority"]),
        due_at            = _parse_dt(row["due_at"]),
        estimated_minutes = row["estimated_minutes"],
        created_at        = _parse_dt(row["created_at"]),
        started_at        = _parse_dt(row["started_at"]),
        completed_at      = _parse_dt(row["completed_at"]),
    )


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------

class Database:
    """
    Manages all SQLite operations for ZeroForge.

    Usage::

        db = Database(Path("~/.zeroforge/tasks.db"))
        db.initialize()
        task_id = db.create_task(Task(title="My task"))
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path

    # ------------------------------------------------------------------ #
    # Connection management                                                #
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        """
        Open and configure a SQLite connection.

        Called at the start of every public method.  We open/close per
        operation rather than holding a long-lived connection to avoid
        threading complications and to keep the API simple.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def initialize(self) -> None:
        """Create tables and apply all pending migrations."""
        try:
            conn = self._connect()
            apply_migrations(conn)
            conn.close()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to initialize database: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Task CRUD                                                            #
    # ------------------------------------------------------------------ #

    def create_task(self, task: Task) -> int:
        """
        Insert a new task and return its assigned ID.

        The task.id field is ignored (AUTOINCREMENT).
        task.created_at must be set before calling.
        """
        sql = """
            INSERT INTO tasks
                (title, description, status, priority, due_at,
                 estimated_minutes, created_at, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task.title,
            task.description,
            task.status.value,
            task.priority.value,
            to_storage_str(task.due_at) if task.due_at else None,
            task.estimated_minutes,
            to_storage_str(task.created_at) if task.created_at else to_storage_str(
                datetime.now(timezone.utc)
            ),
            to_storage_str(task.started_at) if task.started_at else None,
            to_storage_str(task.completed_at) if task.completed_at else None,
        )
        try:
            conn = self._connect()
            cursor = conn.execute(sql, params)
            conn.commit()
            task_id = cursor.lastrowid
            conn.close()
            return task_id
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to create task: {exc}") from exc

    def get_task(self, task_id: int) -> Task:
        """
        Retrieve a task by ID.

        Raises TaskNotFoundError if the ID does not exist.
        """
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            conn.close()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to retrieve task #{task_id}: {exc}") from exc

        if row is None:
            raise TaskNotFoundError(task_id)
        return _row_to_task(row)

    def list_tasks(self, status_filter: Optional[str] = None) -> List[Task]:
        """
        Return all tasks, optionally filtered by status.

        Results are ordered by id (insertion order) for determinism.
        """
        try:
            conn = self._connect()
            if status_filter:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY id",
                    (status_filter.upper(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tasks ORDER BY id"
                ).fetchall()
            conn.close()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to list tasks: {exc}") from exc

        return [_row_to_task(r) for r in rows]

    def update_task(self, task_id: int, **fields) -> None:
        """
        Update specific task fields.

        Accepts keyword arguments matching column names.  datetime values
        are converted to storage strings automatically.
        """
        if not fields:
            return

        # Convert datetime fields to strings.
        datetime_fields = {"due_at", "started_at", "completed_at", "created_at"}
        converted = {}
        for key, val in fields.items():
            if key in datetime_fields and isinstance(val, datetime):
                converted[key] = to_storage_str(val)
            elif hasattr(val, "value"):  # Enum
                converted[key] = val.value
            else:
                converted[key] = val

        set_clause = ", ".join(f"{k} = ?" for k in converted)
        values = list(converted.values()) + [task_id]

        try:
            conn = self._connect()
            # Verify task exists first.
            existing = conn.execute(
                "SELECT id FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if existing is None:
                conn.close()
                raise TaskNotFoundError(task_id)
            conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?", values
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to update task #{task_id}: {exc}") from exc

    def delete_task(self, task_id: int) -> None:
        """
        Delete a task by ID.

        Dependency edges referencing this task are cascade-deleted automatically
        (ON DELETE CASCADE in the schema).

        Raises TaskNotFoundError if the task does not exist.
        """
        try:
            conn = self._connect()
            existing = conn.execute(
                "SELECT id FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if existing is None:
                conn.close()
                raise TaskNotFoundError(task_id)
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to delete task #{task_id}: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Dependency edges                                                     #
    # ------------------------------------------------------------------ #

    def add_dependency(self, task_id: int, depends_on_id: int) -> bool:
        """
        Record that *task_id* depends on *depends_on_id*.

        Returns True if the edge was inserted, False if it already existed
        (idempotent — no error on duplicate).

        Does NOT validate cycles — that responsibility belongs to the engine.
        """
        try:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO dependencies (task_id, depends_on) VALUES (?, ?)",
                    (task_id, depends_on_id),
                )
                conn.commit()
                inserted = True
            except sqlite3.IntegrityError:
                # Duplicate primary key or self-reference check constraint.
                inserted = False
            finally:
                conn.close()
            return inserted
        except sqlite3.Error as exc:
            raise StorageError(
                f"Failed to add dependency #{task_id} → #{depends_on_id}: {exc}"
            ) from exc

    def remove_dependency(self, task_id: int, depends_on_id: int) -> bool:
        """
        Remove a dependency edge.

        Returns True if the edge existed and was removed, False if it did not exist.
        """
        try:
            conn = self._connect()
            cursor = conn.execute(
                "DELETE FROM dependencies WHERE task_id = ? AND depends_on = ?",
                (task_id, depends_on_id),
            )
            conn.commit()
            removed = cursor.rowcount > 0
            conn.close()
            return removed
        except sqlite3.Error as exc:
            raise StorageError(
                f"Failed to remove dependency #{task_id} → #{depends_on_id}: {exc}"
            ) from exc

    def get_dependencies(self, task_id: int) -> List[int]:
        """Return the IDs of tasks that *task_id* directly depends on."""
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT depends_on FROM dependencies WHERE task_id = ? ORDER BY depends_on",
                (task_id,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to get dependencies for #{task_id}: {exc}") from exc

    def get_dependents(self, task_id: int) -> List[int]:
        """Return the IDs of tasks that directly depend on *task_id*."""
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT task_id FROM dependencies WHERE depends_on = ? ORDER BY task_id",
                (task_id,),
            ).fetchall()
            conn.close()
            return [r[0] for r in rows]
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to get dependents for #{task_id}: {exc}") from exc

    def all_edges(self) -> List[Tuple[int, int]]:
        """
        Return all dependency edges as (task_id, depends_on_id) tuples.

        Used by the dependency engine to build the full graph.
        """
        try:
            conn = self._connect()
            rows = conn.execute(
                "SELECT task_id, depends_on FROM dependencies ORDER BY task_id, depends_on"
            ).fetchall()
            conn.close()
            return [(r[0], r[1]) for r in rows]
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to retrieve all edges: {exc}") from exc

    def task_exists(self, task_id: int) -> bool:
        """Return True if a task with *task_id* exists."""
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            conn.close()
            return row is not None
        except sqlite3.Error as exc:
            raise StorageError(f"Failed to check task #{task_id}: {exc}") from exc
