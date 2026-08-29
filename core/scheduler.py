"""
core/scheduler.py
~~~~~~~~~~~~~~~~~
Task scheduling logic for ZeroForge.

The scheduler answers: "Given all current tasks and their dependencies,
in what order should I work on them?"

Algorithm
---------
1. Filter: remove COMPLETED and CANCELLED tasks.
2. Build dependency graph from all edges.
3. Identify READY tasks (all deps completed — see core/dependency.py).
4. Rank READY tasks by a deterministic multi-key sort.
5. Return the ranked list.

Dependency constraints are NEVER violated: only READY tasks enter the
ranking step.  This guarantees you never see "Deploy" ranked above
"Write Tests" when Deploy depends on Write Tests.

Ranking keys (applied in order, all deterministic):
    1. Priority weight (CRITICAL > HIGH > MEDIUM > LOW)  — descending
    2. Overdue flag (overdue tasks rank above non-overdue)  — bool desc
    3. Deadline urgency (earlier deadline = more urgent)  — ascending seconds
       Tasks without a deadline always rank after deadline tasks.
    4. Task age (older created_at = higher priority)  — ascending
    5. Task ID  — ascending (final tiebreaker, always unique)

This avoids starvation: LOW priority tasks with the oldest age will
eventually float above newly created tasks of the same priority group
once deadlines are equal or absent.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from core.models import Task, TaskStatus
from core.dependency import DependencyGraph
from utils.dates import now_utc, deadline_urgency_score, is_overdue


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_tasks(tasks: List[Task], now: Optional[datetime] = None) -> List[Task]:
    """
    Rank a list of tasks by scheduling priority.

    All tasks in *tasks* are assumed to be eligible (READY).
    Returns a new list in descending scheduling priority.

    Parameters
    ----------
    tasks : tasks to rank (should all be READY)
    now   : reference time for deadline calculations (default: UTC now)
    """
    if now is None:
        now = now_utc()

    def sort_key(task: Task) -> Tuple:
        priority_score = task.priority.weight  # higher = more urgent

        overdue = is_overdue(task.due_at, now)
        overdue_flag = 0 if overdue else 1   # 0 sorts first (overdue first)

        urgency = deadline_urgency_score(task.due_at, now)  # smaller = more urgent

        # Older tasks rank higher (smaller created_at timestamp → earlier)
        age_ts = task.created_at.timestamp() if task.created_at else 0.0

        task_id = task.id or 0

        return (
            -priority_score,  # negate so CRITICAL (4) sorts first
            overdue_flag,
            urgency,
            age_ts,
            task_id,
        )

    return sorted(tasks, key=sort_key)


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

def generate_plan(
    tasks: List[Task],
    edges: List[Tuple[int, int]],
    now: Optional[datetime] = None,
) -> List[Task]:
    """
    Generate an execution plan.

    Returns only READY tasks in their recommended execution order.
    BLOCKED, COMPLETED, and CANCELLED tasks are excluded.

    Parameters
    ----------
    tasks : all tasks in the system
    edges : all dependency edges (task_id, depends_on_id)
    now   : reference time (default: UTC now)
    """
    if now is None:
        now = now_utc()

    # Partition tasks.
    completed_ids: Set[int] = {
        t.id for t in tasks
        if t.status == TaskStatus.COMPLETED and t.id is not None
    }
    active_tasks: List[Task] = [
        t for t in tasks
        if t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        and t.id is not None
    ]

    if not active_tasks:
        return []

    # Build dependency graph.
    graph = DependencyGraph(edges)
    active_ids: Set[int] = {t.id for t in active_tasks}  # type: ignore[misc]

    # Classify READY vs BLOCKED.
    status_map: Dict[int, str] = graph.compute_status(active_ids, completed_ids)

    ready_tasks = [
        t for t in active_tasks
        if status_map.get(t.id, "BLOCKED") == "READY"
    ]

    return rank_tasks(ready_tasks, now)


# ---------------------------------------------------------------------------
# Full execution order (topological, ranked within each tier)
# ---------------------------------------------------------------------------

def full_execution_order(
    tasks: List[Task],
    edges: List[Tuple[int, int]],
    now: Optional[datetime] = None,
) -> List[Task]:
    """
    Return ALL active tasks in a valid dependency-respecting execution order,
    ranked within each dependency tier.

    This is useful for 'zeroforge plan --all' to show the complete picture.

    Phase 1 (READY tasks) are ranked and shown first, then Phase 2 (tasks
    that become ready once Phase 1 completes), etc.

    Returns tasks in execution wave order.
    """
    if now is None:
        now = now_utc()

    completed_ids: Set[int] = {
        t.id for t in tasks
        if t.status == TaskStatus.COMPLETED and t.id is not None
    }
    active: List[Task] = [
        t for t in tasks
        if t.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        and t.id is not None
    ]

    if not active:
        return []

    graph = DependencyGraph(edges)
    task_by_id: Dict[int, Task] = {t.id: t for t in active}  # type: ignore[misc]

    simulated_completed: Set[int] = set(completed_ids)
    remaining: Set[int] = {t.id for t in active}  # type: ignore[misc]
    result: List[Task] = []

    while remaining:
        status_map = graph.compute_status(remaining, simulated_completed)
        wave = [
            task_by_id[tid] for tid in remaining
            if status_map.get(tid) == "READY"
        ]

        if not wave:
            # Remaining tasks are all blocked (shouldn't happen without a cycle)
            # but add them as-is to avoid infinite loop.
            result.extend(sorted(task_by_id[tid] for tid in remaining))
            break

        ranked_wave = rank_tasks(wave, now)
        result.extend(ranked_wave)

        for t in ranked_wave:
            remaining.discard(t.id)
            simulated_completed.add(t.id)

    return result
