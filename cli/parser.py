"""
cli/parser.py
~~~~~~~~~~~~~
Argparse configuration for ZeroForge CLI.

All argument parsing lives here.  No business logic.
"""
from __future__ import annotations

import argparse

VERSION = "1.0.0"


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""

    parser = argparse.ArgumentParser(
        prog="zeroforge",
        description=(
            "ZeroForge — Zero-dependency local task engine.\n"
            "Understands dependencies, constraints, priorities, and deadlines\n"
            "to determine what you can work on next."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  zeroforge add \"Design DB\" --priority high\n"
            "  zeroforge add \"Build API\" --after 1 --priority critical\n"
            "  zeroforge ready\n"
            "  zeroforge done 1\n"
            "  zeroforge plan\n"
            "  zeroforge graph\n"
        ),
    )

    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"ZeroForge {VERSION}",
    )

    parser.add_argument(
        "--db",
        metavar="PATH",
        help="Path to the SQLite database file (default: ~/.zeroforge/tasks.db)",
        default=None,
    )

    sub = parser.add_subparsers(dest="command", title="commands", metavar="<command>")

    # ------------------------------------------------------------------ #
    # add                                                                  #
    # ------------------------------------------------------------------ #
    p_add = sub.add_parser("add", help="Create a new task")
    p_add.add_argument("title", help="Short task description")
    p_add.add_argument(
        "--priority", "-p",
        default="medium",
        metavar="LEVEL",
        help="Priority: low, medium, high, critical  (default: medium)",
    )
    p_add.add_argument(
        "--description", "-d",
        default="",
        metavar="TEXT",
        help="Optional longer description",
    )
    p_add.add_argument(
        "--due",
        default=None,
        metavar="DATE",
        help="Deadline: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS",
    )
    p_add.add_argument(
        "--estimate", "-e",
        type=int,
        default=None,
        metavar="MINUTES",
        help="Estimated effort in minutes",
    )
    p_add.add_argument(
        "--after", "-a",
        type=int,
        nargs="+",
        default=None,
        metavar="ID",
        help="Task ID(s) this task depends on (can specify multiple)",
    )

    # ------------------------------------------------------------------ #
    # list                                                                 #
    # ------------------------------------------------------------------ #
    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument(
        "--status", "-s",
        default=None,
        metavar="STATUS",
        help="Filter by status: pending, in_progress, completed, cancelled",
    )

    # ------------------------------------------------------------------ #
    # show                                                                 #
    # ------------------------------------------------------------------ #
    p_show = sub.add_parser("show", help="Show task details")
    p_show.add_argument("id", type=int, help="Task ID")

    # ------------------------------------------------------------------ #
    # update                                                               #
    # ------------------------------------------------------------------ #
    p_update = sub.add_parser("update", help="Update task fields")
    p_update.add_argument("id", type=int, help="Task ID")
    p_update.add_argument("--title", "-t", default=None, help="New title")
    p_update.add_argument("--description", "-d", default=None, help="New description")
    p_update.add_argument("--priority", "-p", default=None, metavar="LEVEL", help="New priority")
    p_update.add_argument("--due", default=None, metavar="DATE", help="New deadline")
    p_update.add_argument(
        "--clear-due", action="store_true", help="Remove the deadline"
    )
    p_update.add_argument(
        "--estimate", "-e", type=int, default=None, metavar="MINUTES",
        help="New effort estimate"
    )

    # ------------------------------------------------------------------ #
    # delete                                                               #
    # ------------------------------------------------------------------ #
    p_delete = sub.add_parser("delete", help="Delete a task")
    p_delete.add_argument("id", type=int, help="Task ID")
    p_delete.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # ------------------------------------------------------------------ #
    # start                                                                #
    # ------------------------------------------------------------------ #
    p_start = sub.add_parser("start", help="Mark a task as in-progress")
    p_start.add_argument("id", type=int, help="Task ID")

    # ------------------------------------------------------------------ #
    # done                                                                 #
    # ------------------------------------------------------------------ #
    p_done = sub.add_parser("done", help="Mark a task as completed")
    p_done.add_argument("id", type=int, help="Task ID")

    # ------------------------------------------------------------------ #
    # cancel                                                               #
    # ------------------------------------------------------------------ #
    p_cancel = sub.add_parser("cancel", help="Cancel a task")
    p_cancel.add_argument("id", type=int, help="Task ID")

    # ------------------------------------------------------------------ #
    # dep (dependency sub-commands)                                        #
    # ------------------------------------------------------------------ #
    p_dep = sub.add_parser("dep", help="Manage task dependencies")
    dep_sub = p_dep.add_subparsers(dest="dep_command", title="dep commands", metavar="<action>")

    # dep add
    p_dep_add = dep_sub.add_parser("add", help="Add a dependency: TASK depends on DEP")
    p_dep_add.add_argument("id", type=int, help="Task ID (the dependent task)")
    p_dep_add.add_argument("--on", type=int, required=True, metavar="DEP_ID",
                           help="ID of the task to depend on")

    # dep remove
    p_dep_rm = dep_sub.add_parser("remove", help="Remove a dependency")
    p_dep_rm.add_argument("id", type=int, help="Task ID (the dependent task)")
    p_dep_rm.add_argument("--on", type=int, required=True, metavar="DEP_ID",
                          help="ID of the dependency to remove")

    # dep list
    p_dep_ls = dep_sub.add_parser("list", help="List dependencies for a task")
    p_dep_ls.add_argument("id", type=int, help="Task ID")

    # ------------------------------------------------------------------ #
    # ready                                                                #
    # ------------------------------------------------------------------ #
    sub.add_parser("ready", help="List tasks ready to work on (all deps satisfied)")

    # ------------------------------------------------------------------ #
    # blocked                                                              #
    # ------------------------------------------------------------------ #
    sub.add_parser("blocked", help="List tasks that are blocked by incomplete dependencies")

    # ------------------------------------------------------------------ #
    # plan                                                                 #
    # ------------------------------------------------------------------ #
    sub.add_parser("plan", help="Generate a full dependency-aware execution plan")

    # ------------------------------------------------------------------ #
    # graph                                                                #
    # ------------------------------------------------------------------ #
    sub.add_parser("graph", help="Visualise the dependency graph")

    return parser
