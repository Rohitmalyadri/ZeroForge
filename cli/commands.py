"""
cli/commands.py
~~~~~~~~~~~~~~~
Command handler functions for ZeroForge.

Each function corresponds to one CLI sub-command. Handlers:
1. Call engine methods.
2. Format output for stdout.
3. Write errors to stderr.
4. Return an exit code (0 = success, non-zero = failure).

The handlers must NOT import sqlite3 or call the database directly.
"""
from __future__ import annotations

import sys
from typing import List, Optional

from core.engine import Engine
from core.models import TaskStatus, Priority
from utils.dates import format_display, is_overdue, now_utc
from utils.errors import (
    ZeroForgeError,
    DependencyCycleError,
    TaskNotFoundError,
    DependencyError,
    InvalidTaskError,
)
from utils.formatting import (
    format_task_row,
    format_task_header,
    format_task_divider,
    section_header,
    section_divider,
    truncate,
    render_graph_ascii,
)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _out(msg: str = "") -> None:
    """Print to stdout."""
    print(msg)


def _err(msg: str) -> None:
    """Print to stderr."""
    print(f"ERROR: {msg}", file=sys.stderr)


def _success(msg: str) -> None:
    """Print a success message to stdout."""
    print(f"[OK] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _task_row(task, computed_status: Optional[str] = None) -> str:
    due_str = format_display(task.due_at) if task.due_at else "-"
    return format_task_row(
        task_id       = task.id,
        priority_str  = task.priority.value,
        status_str    = task.status.value,
        title         = task.title,
        due_str       = due_str,
        computed_str  = computed_status,
    )


def _print_task_table(tasks, computed_map=None, header_override: Optional[str] = None) -> None:
    """Print a formatted task table to stdout."""
    if not tasks:
        _out("  (no tasks)")
        return

    _out(format_task_header())
    _out(format_task_divider())
    for task in tasks:
        computed = (computed_map or {}).get(task.id)
        _out(_task_row(task, computed))


# ---------------------------------------------------------------------------
# Command: add
# ---------------------------------------------------------------------------

def cmd_add(engine: Engine, args) -> int:
    try:
        task = engine.add_task(
            title             = args.title,
            priority          = args.priority,
            description       = getattr(args, "description", "") or "",
            due_at            = getattr(args, "due", None),
            estimated_minutes = getattr(args, "estimate", None),
            after             = getattr(args, "after", None),
        )
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Created task #{task.id}: {task.title}")
    _out(f"   Priority  : {task.priority.value}")
    if task.due_at:
        _out(f"   Due       : {format_display(task.due_at)}")
    if task.estimated_minutes:
        _out(f"   Estimate  : {task.estimated_minutes} min")

    after = getattr(args, "after", None) or []
    for dep_id in after:
        _out(f"   Dependency: #{task.id} -> #{dep_id}")

    return 0


# ---------------------------------------------------------------------------
# Command: list
# ---------------------------------------------------------------------------

def cmd_list(engine: Engine, args) -> int:
    status_filter = getattr(args, "status", None)
    try:
        tasks = engine.list_tasks(status_filter)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    if status_filter:
        title = f"TASKS - STATUS: {status_filter.upper()}"
    else:
        title = "ALL TASKS"

    _out(section_header(title))
    _out()

    if not tasks:
        _out("  No tasks found.")
        return 0

    # Build computed status map for all active tasks.
    edges = engine._db.all_edges()
    from core.dependency import DependencyGraph
    from core.models import TaskStatus as TS
    completed_ids = {t.id for t in tasks if t.status == TS.COMPLETED}
    active_ids    = {t.id for t in tasks if t.status not in (TS.COMPLETED, TS.CANCELLED)}
    graph = DependencyGraph(edges)
    status_map = graph.compute_status(active_ids, completed_ids)

    _print_task_table(tasks, computed_map=status_map)
    _out()
    _out(f"  {len(tasks)} task(s) total.")
    return 0


# ---------------------------------------------------------------------------
# Command: show
# ---------------------------------------------------------------------------

def cmd_show(engine: Engine, args) -> int:
    try:
        view = engine.show_task(args.id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    task = view["task"]
    computed = view["computed_status"]
    depends_on = view["depends_on"]
    dependents = view["dependents"]

    _out(section_header(f"TASK #{task.id}"))
    _out()
    _out(f"  Title       : {task.title}")
    _out(f"  Status      : {task.status.value}  ->  {computed}")
    _out(f"  Priority    : {task.priority.value}")
    _out(f"  Due         : {format_display(task.due_at)}")
    _out(f"  Estimate    : {task.estimated_minutes or '-'} min")
    _out(f"  Created     : {format_display(task.created_at)}")
    _out(f"  Started     : {format_display(task.started_at)}")
    _out(f"  Completed   : {format_display(task.completed_at)}")
    if task.description:
        _out(f"  Description : {task.description}")

    _out()
    _out(f"  Depends on  : " + (
        ", ".join(f"#{t.id} {t.title}" for t in depends_on) or "(none)"
    ))
    _out(f"  Dependents  : " + (
        ", ".join(f"#{t.id} {t.title}" for t in dependents) or "(none)"
    ))

    return 0


# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------

def cmd_update(engine: Engine, args) -> int:
    try:
        task = engine.update_task(
            task_id           = args.id,
            title             = getattr(args, "title", None),
            description       = getattr(args, "description", None),
            priority          = getattr(args, "priority", None),
            due_at            = getattr(args, "due", None),
            estimated_minutes = getattr(args, "estimate", None),
            clear_due         = getattr(args, "clear_due", False),
        )
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Updated task #{task.id}: {task.title}")
    return 0


# ---------------------------------------------------------------------------
# Command: delete
# ---------------------------------------------------------------------------

def cmd_delete(engine: Engine, args) -> int:
    task_id = args.id
    skip_confirm = getattr(args, "yes", False)

    # Confirm.
    if not skip_confirm:
        try:
            task = engine.get_task(task_id)
        except ZeroForgeError as exc:
            _err(str(exc))
            return 1

        _warn(f"About to delete task #{task_id}: '{task.title}'")
        _warn("All dependency edges involving this task will also be removed.")
        try:
            answer = input("Type 'yes' to confirm: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            _out("\nAborted.")
            return 1
        if answer != "yes":
            _out("Aborted.")
            return 1

    try:
        engine.delete_task(task_id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Deleted task #{task_id}.")
    return 0


# ---------------------------------------------------------------------------
# Command: start
# ---------------------------------------------------------------------------

def cmd_start(engine: Engine, args) -> int:
    try:
        task = engine.start_task(args.id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Started task #{task.id}: {task.title}")
    return 0


# ---------------------------------------------------------------------------
# Command: done
# ---------------------------------------------------------------------------

def cmd_done(engine: Engine, args) -> int:
    try:
        task = engine.complete_task(args.id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Completed task #{task.id}: {task.title}")

    # Show what just became unblocked.
    newly_ready = engine.ready_tasks()
    if newly_ready:
        _out()
        _out("  Tasks now ready:")
        for t in newly_ready:
            _out(f"    #{t.id}  {t.priority.value:<8}  {t.title}")

    return 0


# ---------------------------------------------------------------------------
# Command: cancel
# ---------------------------------------------------------------------------

def cmd_cancel(engine: Engine, args) -> int:
    try:
        task = engine.cancel_task(args.id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Cancelled task #{task.id}: {task.title}")
    return 0


# ---------------------------------------------------------------------------
# Command: dep add
# ---------------------------------------------------------------------------

def cmd_dep_add(engine: Engine, args) -> int:
    task_id = args.id
    dep_id  = args.on

    try:
        engine.add_dependency(task_id, dep_id)
    except DependencyCycleError as exc:
        _err(str(exc))
        return 1
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Dependency added: #{task_id} now depends on #{dep_id}.")
    return 0


# ---------------------------------------------------------------------------
# Command: dep remove
# ---------------------------------------------------------------------------

def cmd_dep_remove(engine: Engine, args) -> int:
    try:
        engine.remove_dependency(args.id, args.on)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _success(f"Removed dependency: #{args.id} no longer depends on #{args.on}.")
    return 0


# ---------------------------------------------------------------------------
# Command: dep list
# ---------------------------------------------------------------------------

def cmd_dep_list(engine: Engine, args) -> int:
    try:
        view = engine.show_task(args.id)
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    task = view["task"]
    _out(section_header(f"DEPENDENCIES FOR #{task.id}: {task.title}"))
    _out()

    deps = view["depends_on"]
    if deps:
        _out("  This task depends on:")
        for t in deps:
            _out(f"    #{t.id}  {t.priority.value:<8}  {t.status.value:<11}  {t.title}")
    else:
        _out("  This task has no dependencies.")

    _out()

    dependents = view["dependents"]
    if dependents:
        _out("  Tasks that depend on this task:")
        for t in dependents:
            _out(f"    #{t.id}  {t.priority.value:<8}  {t.status.value:<11}  {t.title}")
    else:
        _out("  No tasks depend on this task.")

    return 0


# ---------------------------------------------------------------------------
# Command: ready
# ---------------------------------------------------------------------------

def cmd_ready(engine: Engine, args) -> int:
    try:
        tasks = engine.ready_tasks()
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _out(section_header("READY TASKS"))
    _out()

    if not tasks:
        _out("  No tasks are currently ready.")
        _out("  (All pending tasks may be blocked, or no tasks exist.)")
        return 0

    _out(format_task_header())
    _out(format_task_divider())
    for task in tasks:
        _out(_task_row(task, "READY"))

    _out()
    _out(f"  {len(tasks)} task(s) ready.")
    return 0


# ---------------------------------------------------------------------------
# Command: blocked
# ---------------------------------------------------------------------------

def cmd_blocked(engine: Engine, args) -> int:
    try:
        blocked = engine.blocked_tasks()
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _out(section_header("BLOCKED TASKS"))
    _out()

    if not blocked:
        _out("  No tasks are currently blocked.")
        return 0

    for (task, blocker_ids) in blocked:
        due_str = format_display(task.due_at) if task.due_at else "-"
        _out(_task_row(task, "BLOCKED"))
        blockers_str = ", ".join(f"#{i}" for i in blocker_ids)
        _out(f"       +-- blocked by: {blockers_str}")

    _out()
    _out(f"  {len(blocked)} task(s) blocked.")
    return 0


# ---------------------------------------------------------------------------
# Command: plan
# ---------------------------------------------------------------------------

def cmd_plan(engine: Engine, args) -> int:
    try:
        planned = engine.generate_plan()
    except DependencyCycleError as exc:
        _err(str(exc))
        _err("Fix the cycle before generating a plan.")
        return 1
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _out(section_header("EXECUTION PLAN"))
    _out()

    if not planned:
        _out("  No active tasks to plan.")
        return 0

    # Group into waves.
    edges = engine._db.all_edges()
    from core.dependency import DependencyGraph
    from core.models import TaskStatus as TS
    all_tasks = engine._db.list_tasks()
    completed_ids = {t.id for t in all_tasks if t.status == TS.COMPLETED}

    wave = 1
    shown_ids = set(completed_ids)

    for task in planned:
        if task.id not in shown_ids:
            graph = DependencyGraph(edges)
            status = graph.compute_status({task.id}, shown_ids)
            is_ready = status.get(task.id) == "READY"

            prefix = f"  [{wave:>2}] " if is_ready else "       "
            due_str = f"  due {format_display(task.due_at)}" if task.due_at else ""
            overdue_tag = " [OVERDUE]" if is_overdue(task.due_at) else ""
            _out(
                f"{prefix}#{task.id:<4} {task.priority.value:<8} "
                f"{task.title}{due_str}{overdue_tag}"
            )
            shown_ids.add(task.id)
            wave += 1

    _out()
    _out(f"  {len(planned)} task(s) in plan.")
    return 0


# ---------------------------------------------------------------------------
# Command: graph
# ---------------------------------------------------------------------------

def cmd_graph(engine: Engine, args) -> int:
    try:
        data = engine.get_graph_data()
    except DependencyCycleError as exc:
        _err(str(exc))
        return 1
    except ZeroForgeError as exc:
        _err(str(exc))
        return 1

    _out(section_header("DEPENDENCY GRAPH"))
    _out()

    if not data["tasks"]:
        _out("  No tasks exist.")
        return 0

    ascii_graph = render_graph_ascii(
        tasks      = data["tasks"],
        edges      = data["edges"],
        topo_order = data["topo_order"],
    )
    for line in ascii_graph.splitlines():
        _out("  " + line)

    _out()

    # Print edge legend.
    if data["edges"]:
        _out("  Dependencies:")
        for (tid, dep) in data["edges"]:
            task_title = data["tasks"].get(tid, "?")
            dep_title  = data["tasks"].get(dep, "?")
            _out(f"    #{tid} '{truncate(task_title, 30)}' depends on #{dep} '{truncate(dep_title, 30)}'")

    return 0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch(engine: Engine, args) -> int:
    """Route parsed arguments to the correct command handler."""
    command = args.command

    if command == "add":
        return cmd_add(engine, args)
    elif command == "list":
        return cmd_list(engine, args)
    elif command == "show":
        return cmd_show(engine, args)
    elif command == "update":
        return cmd_update(engine, args)
    elif command == "delete":
        return cmd_delete(engine, args)
    elif command == "start":
        return cmd_start(engine, args)
    elif command == "done":
        return cmd_done(engine, args)
    elif command == "cancel":
        return cmd_cancel(engine, args)
    elif command == "dep":
        dep_command = getattr(args, "dep_command", None)
        if dep_command == "add":
            return cmd_dep_add(engine, args)
        elif dep_command == "remove":
            return cmd_dep_remove(engine, args)
        elif dep_command == "list":
            return cmd_dep_list(engine, args)
        else:
            _err("Missing dep sub-command. Try: dep add, dep remove, dep list")
            return 1
    elif command == "ready":
        return cmd_ready(engine, args)
    elif command == "blocked":
        return cmd_blocked(engine, args)
    elif command == "plan":
        return cmd_plan(engine, args)
    elif command == "graph":
        return cmd_graph(engine, args)
    else:
        return 2
