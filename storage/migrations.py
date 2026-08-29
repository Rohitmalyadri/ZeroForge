"""
storage/migrations.py
~~~~~~~~~~~~~~~~~~~~~
Simple schema version tracking for ZeroForge.

We use a 'schema_version' table to track applied migrations.  Each migration
is a plain SQL string with a unique version number.

This is intentionally minimal — a 72-hour hackathon project does not need a
full migration framework, but should be able to evolve its schema cleanly.
"""
from __future__ import annotations

import sqlite3
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------
# Each entry: (version: int, description: str, sql: str)
# Migrations are applied in version order, exactly once.

MIGRATIONS: List[Tuple[int, str, str]] = [
    (
        1,
        "Initial schema: tasks + dependencies tables",
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            title             TEXT    NOT NULL,
            description       TEXT    NOT NULL DEFAULT '',
            status            TEXT    NOT NULL DEFAULT 'PENDING',
            priority          TEXT    NOT NULL DEFAULT 'MEDIUM',
            due_at            TEXT,
            estimated_minutes INTEGER,
            created_at        TEXT    NOT NULL,
            started_at        TEXT,
            completed_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS dependencies (
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            depends_on  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, depends_on),
            CHECK (task_id != depends_on)
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
        CREATE INDEX IF NOT EXISTS idx_deps_task_id   ON dependencies(task_id);
        CREATE INDEX IF NOT EXISTS idx_deps_depends   ON dependencies(depends_on);
        """,
    ),
]


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

def _ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create the schema_version table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            description TEXT    NOT NULL,
            applied_at  TEXT    NOT NULL
        )
        """
    )
    conn.commit()


def _current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if none."""
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    ).fetchone()
    return row[0] if row else 0


def apply_migrations(conn: sqlite3.Connection) -> None:
    """
    Apply any unapplied migrations in version order.

    Safe to call on every startup — already-applied migrations are skipped.
    """
    from datetime import datetime, timezone

    _ensure_version_table(conn)
    current = _current_version(conn)

    for version, description, sql in sorted(MIGRATIONS, key=lambda m: m[0]):
        if version <= current:
            continue  # already applied

        # Execute the migration SQL (may contain multiple statements).
        conn.executescript(sql)

        # Record the applied version.
        conn.execute(
            "INSERT INTO schema_version (version, description, applied_at) VALUES (?, ?, ?)",
            (
                version,
                description,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            ),
        )
        conn.commit()
