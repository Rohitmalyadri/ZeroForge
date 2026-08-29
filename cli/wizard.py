"""
cli/wizard.py
~~~~~~~~~~~~~
Guided step-by-step task management wizard.

A conversational, menu-driven interface for non-CLI users.
Uses only Python standard library (input() prompting, no LLM).

Available flows:
- Create a new task (step-by-step with smart defaults)
- View and complete tasks
- Show the dependency graph
- See the execution plan
"""
from __future__ import annotations

import sys
from typing import Optional

from core.engine import Engine
from storage.database import Database
from utils.errors import ZeroForgeError
from utils.dates import now_utc
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _prompt(question: str, default: Optional[str] = None) -> str:
    """
    Prompt the user for a line of input.
    Returns the stripped response, or default if empty.
    """
    if default:
        suffix = f" [{default}]"
    else:
        suffix = ""
    try:
        response = input(f"  {question}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
    if not response and default:
        return default
    return response


def _confirm(question: str, default: bool = False) -> bool:
    """Ask a yes/no question. Returns True if user confirms."""
    suffix = " (Y/n)" if default else " (y/N)"
    response = _prompt(question + suffix, "")
    if not response:
        return default
    return response.lower() in ("y", "yes", "true", "1")


def _choose(question: str, options: list[str]) -> Optional[str]:
    """
    Ask user to choose from a list of options.
    Returns the chosen option, or None if cancelled.
    """
    print(f"\n  {question}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    choice = _prompt("Choose a number (or 'cancel')")
    if choice.lower() in ("cancel", "c", "q", "quit"):
        return None
    try:
        idx = int(choice)
        if 1 <= idx <= len(options):
            return options[idx - 1]
    except ValueError:
        # Try matching by prefix
        for opt in options:
            if opt.lower().startswith(choice.lower()):
                return opt
    print(f"  Invalid choice.")
    return None


def _pause() -> None:
    """Press enter to continue."""
    try:
        input("\n  Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        print()


def _section(title: str) -> None:
    """Print a section header."""
    print()
    print("  " + "=" * 50)
    print(f"  {title}")
    print("  " + "=" * 50)


# ---------------------------------------------------------------------------
# Natural language date parsing (stdlib only)
# ---------------------------------------------------------------------------

def _parse_natural_date(text: str) -> Optional[datetime]:
    """
    Parse a human-friendly date string using stdlib only.

    Supports:
    - today, tomorrow, yesterday
    - next <day> (Monday-Sunday)
    - in N days / N days
    - YYYY-MM-DD (fallback)
    """
    text = text.strip().lower()
    if not text:
        return None

    now = now_utc()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if text == "today":
        return today.replace(hour=23, minute=59, second=59)
    if text == "tomorrow":
        return (today + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    if text == "yesterday":
        return (today - timedelta(days=1)).replace(hour=23, minute=59, second=59)

    # "in N days" or "N days"
    if text.startswith("in "):
        rest = text[3:].strip()
        if rest.endswith(" days") or rest.endswith(" day"):
            try:
                n = int(rest.split()[0])
                return (today + timedelta(days=n)).replace(hour=23, minute=59, second=59)
            except (ValueError, IndexError):
                pass

    # "next monday" etc.
    days = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    for day_name, day_offset in days.items():
        if text == day_name or text == f"next {day_name}":
            current_weekday = today.weekday()
            if text.startswith("next"):
                # Next week
                target = current_weekday + 7
            else:
                # This week, but must be in future
                target = day_offset
                if target <= current_weekday:
                    target += 7
            return (today + timedelta(days=target - current_weekday)).replace(
                hour=23, minute=59, second=59
            )

    # Fallback to ISO format
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return None


# ---------------------------------------------------------------------------
# Wizard flows
# ---------------------------------------------------------------------------

def wizard_create_task(engine: Engine) -> int:
    """Step-by-step guided task creation."""
    _section("Create a New Task")

    # Step 1: Title
    title = _prompt("What do you want to do? (title)")
    if not title:
        print("  Task creation cancelled (no title).")
        return 0

    # Step 2: Priority
    print("\n  What's the priority level?")
    priority = _choose("Select priority:", [
        "critical", "high", "medium", "low"
    ])
    if priority is None:
        print("  Task creation cancelled.")
        return 0

    # Step 3: Description
    description = _prompt("Add a description? (optional, press Enter to skip)")

    # Step 4: Deadline
    print("\n  Set a deadline?")
    print("    (Examples: 'tomorrow', 'next friday', 'in 7 days', '2026-12-31', or skip)")
    due_str = _prompt("Deadline", "")
    due_at = None
    if due_str:
        due_at = _parse_natural_date(due_str)
        if due_at is None:
            print(f"  Couldn't parse '{due_str}' as a date. Skipping deadline.")
        else:
            print(f"    → Deadline set to {due_at.strftime('%Y-%m-%d %H:%M UTC')}")

    # Step 5: Estimate
    estimate_str = _prompt("Estimated effort in minutes? (optional, press Enter to skip)")
    estimate = None
    if estimate_str:
        try:
            estimate = int(estimate_str)
        except ValueError:
            print("  Invalid number, skipping estimate.")

    # Step 6: Dependencies
    after = None
    try:
        all_tasks = engine.list_tasks()
    except ZeroForgeError:
        all_tasks = []

    if all_tasks:
        print("\n  Does this task depend on any existing tasks?")
        print(f"    (You have {len(all_tasks)} task(s). List IDs, comma-separated, or skip)")
        deps_str = _prompt("Dependencies", "")
        if deps_str:
            after = []
            for part in deps_str.split(","):
                try:
                    after.append(int(part.strip()))
                except ValueError:
                    print(f"    Skipping invalid ID: {part}")

    # Summary
    _section("Summary")
    print(f"  Title       : {title}")
    print(f"  Priority    : {priority}")
    if description:
        print(f"  Description : {description}")
    if due_at:
        print(f"  Deadline    : {due_at.strftime('%Y-%m-%d %H:%M UTC')}")
    if estimate:
        print(f"  Estimate    : {estimate} min")
    if after:
        print(f"  Depends on  : {', '.join(f'#{i}' for i in after)}")
    print()

    if not _confirm("Create this task?", default=True):
        print("  Cancelled.")
        return 0

    # Create the task
    try:
        task = engine.add_task(
            title=title,
            priority=priority,
            description=description or "",
            due_at=due_str if due_at else None,
            estimated_minutes=estimate,
            after=after,
        )
        print(f"\n  [OK] Created task #{task.id}: {task.title}")
        return 0
    except ZeroForgeError as exc:
        print(f"\n  ERROR: {exc}", file=sys.stderr)
        return 1


def wizard_view_tasks(engine: Engine) -> int:
    """Show tasks in a friendly way."""
    _section("Your Tasks")

    try:
        tasks = engine.list_tasks()
    except ZeroForgeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return 1

    if not tasks:
        print("  No tasks yet. Try creating one first!")
        _pause()
        return 0

    # Group by status
    pending = [t for t in tasks if t.status.value == "PENDING"]
    in_progress = [t for t in tasks if t.status.value == "IN_PROGRESS"]
    completed = [t for t in tasks if t.status.value == "COMPLETED"]
    cancelled = [t for t in tasks if t.status.value == "CANCELLED"]

    print(f"\n  Total: {len(tasks)} task(s)")
    if in_progress:
        print(f"\n  ▶ In Progress ({len(in_progress)}):")
        for t in in_progress:
            print(f"    #{t.id:<4} [{t.priority.value:<8}] {t.title}")
    if pending:
        print(f"\n  ◷ Pending ({len(pending)}):")
        for t in pending:
            print(f"    #{t.id:<4} [{t.priority.value:<8}] {t.title}")
    if completed:
        print(f"\n  ✓ Completed ({len(completed)}):")
        for t in completed:
            print(f"    #{t.id:<4} [{t.priority.value:<8}] {t.title}")
    if cancelled:
        print(f"\n  ✗ Cancelled ({len(cancelled)}):")
        for t in cancelled:
            print(f"    #{t.id:<4} [{t.priority.value:<8}] {t.title}")

    print()
    _pause()
    return 0


def wizard_complete_task(engine: Engine) -> int:
    """Guide user to mark a task as done."""
    _section("Complete a Task")

    try:
        ready = engine.ready_tasks()
        in_progress_ids = [
            t for t in engine.list_tasks() if t.status.value == "IN_PROGRESS"
        ]
    except ZeroForgeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return 1

    candidates = in_progress_ids + ready
    if not candidates:
        print("  No tasks are ready or in progress. Nothing to complete.")
        _pause()
        return 0

    print("  Which task did you complete?\n")
    for i, t in enumerate(candidates, 1):
        marker = "▶" if t.status.value == "IN_PROGRESS" else "○"
        print(f"    {i}. {marker} #{t.id} [{t.priority.value:<8}] {t.title}")

    choice = _prompt("\nChoose a number (or 'cancel')")
    if choice.lower() in ("cancel", "c", "q"):
        return 0

    try:
        idx = int(choice)
        if 1 <= idx <= len(candidates):
            task = candidates[idx - 1]
        else:
            print("  Invalid choice.")
            return 1
    except ValueError:
        print("  Invalid choice.")
        return 1

    if _confirm(f"Mark task #{task.id} ({task.title}) as complete?", default=True):
        try:
            engine.complete_task(task.id)
            print(f"\n  [OK] Task #{task.id} marked as complete.")
        except ZeroForgeError as exc:
            print(f"\n  ERROR: {exc}", file=sys.stderr)
            return 1

    return 0


def wizard_view_plan(engine: Engine) -> int:
    """Show the execution plan in a friendly way."""
    _section("Execution Plan")

    try:
        plan = engine.generate_plan()
        ready = engine.ready_tasks()
        blocked = engine.blocked_tasks()
    except ZeroForgeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return 1

    if not plan and not blocked:
        print("  No active tasks. You're all caught up!")
        _pause()
        return 0

    if ready:
        print(f"\n  🎯 Ready to work on ({len(ready)}):")
        for i, t in enumerate(ready, 1):
            due = ""
            if t.due_at:
                from utils.dates import is_overdue
                if is_overdue(t.due_at):
                    due = " [OVERDUE]"
                else:
                    due = f" (due {t.due_at.strftime('%Y-%m-%d')})"
            print(f"    {i}. #{t.id} [{t.priority.value:<8}] {t.title}{due}")

    if blocked:
        print(f"\n  🔒 Blocked ({len(blocked)}):")
        for t, blockers in blocked:
            blocker_str = ", ".join(f"#{b}" for b in blockers)
            print(f"    #{t.id} [{t.priority.value:<8}] {t.title} (waiting on: {blocker_str})")

    print()
    _pause()
    return 0


def wizard_view_graph(engine: Engine) -> int:
    """Show the dependency graph."""
    _section("Dependency Graph")

    try:
        from cli.commands import cmd_graph
        from cli.parser import build_parser
        parser = build_parser()
        args = parser.parse_args(["graph"])
        result = cmd_graph(engine, args)
    except ZeroForgeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return 1

    _pause()
    return result


# ---------------------------------------------------------------------------
# Main wizard loop
# ---------------------------------------------------------------------------

def run_wizard(db: Database) -> int:
    """
    Run the guided wizard menu loop.
    Returns the exit code.
    """
    engine = Engine(db)

    # Welcome
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     ZeroForge Guided Wizard              ║")
    print("  ║     Step-by-step task management         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print("  This wizard will help you manage your tasks without")
    print("  needing to remember command-line arguments.")
    print()

    actions = [
        ("Create a new task", wizard_create_task),
        ("View my tasks", wizard_view_tasks),
        ("Complete a task", wizard_complete_task),
        ("See what I should work on", wizard_view_plan),
        ("View dependency graph", wizard_view_graph),
        ("Exit the wizard", None),
    ]

    while True:
        print()
        print("  What would you like to do?")
        for i, (label, _) in enumerate(actions, 1):
            print(f"    {i}. {label}")
        print()

        choice = _prompt("Choose a number")
        if not choice:
            continue

        if choice.lower() in ("q", "quit", "exit"):
            print("  Goodbye!")
            return 0

        try:
            idx = int(choice)
        except ValueError:
            print("  Please enter a number.")
            continue

        if idx < 1 or idx > len(actions):
            print("  Invalid choice.")
            continue

        label, action = actions[idx - 1]
        if action is None:
            # Exit
            print("  Goodbye!")
            return 0

        # Run the chosen action
        result = action(engine)
        if result != 0:
            return result
