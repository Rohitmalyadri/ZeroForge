"""
utils/formatting.py
~~~~~~~~~~~~~~~~~~~
Lightweight terminal formatting for ZeroForge.

No third-party libraries (no Rich, no colorama).
Uses safe, portable ASCII formatting that works reliably across all
operating systems and terminal encodings (Windows cmd, PowerShell, macOS, Linux).

Public API
----------
- render_table(headers, rows, col_widths) -> str
- format_id(task_id) -> str
- format_priority(priority_str) -> str
- format_status(status_str, computed?) -> str
- truncate(s, max_len) -> str
- section_header(title) -> str
- indent(text, spaces) -> str
"""
from __future__ import annotations

from typing import List, Optional, Sequence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PRIORITY_WIDTH = 8   # "CRITICAL" is 8 chars
_STATUS_WIDTH   = 11  # "IN_PROGRESS" is 11 chars
_ID_WIDTH       = 4   # "#999"


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def truncate(s: str, max_len: int, suffix: str = "...") -> str:
    """Truncate *s* to *max_len* chars, appending *suffix* if truncated."""
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def pad_right(s: str, width: int) -> str:
    """Left-align *s* in a field of *width* characters."""
    return s[:width].ljust(width)


def pad_left(s: str, width: int) -> str:
    """Right-align *s* in a field of *width* characters."""
    return s[:width].rjust(width)


def indent(text: str, spaces: int = 2) -> str:
    """Indent every line of *text* by *spaces* spaces."""
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------

def section_header(title: str, width: int = 60) -> str:
    """
    Render a section header with standard ASCII separator bars.
    """
    bar = "=" * width
    return f"{bar}\n{title}\n{bar}"


def section_divider(width: int = 60) -> str:
    """Return a thin horizontal divider."""
    return "-" * width


# ---------------------------------------------------------------------------
# Field formatters
# ---------------------------------------------------------------------------

def format_id(task_id: int) -> str:
    """Return '#N' padded to _ID_WIDTH."""
    return f"#{task_id}"


def format_priority(priority_str: str) -> str:
    """Return priority string padded to _PRIORITY_WIDTH."""
    return pad_right(priority_str.upper(), _PRIORITY_WIDTH)


def format_status(status_str: str, computed_str: Optional[str] = None) -> str:
    """
    Format status for display. If *computed_str* is provided (READY/BLOCKED),
    it is shown.
    """
    if computed_str:
        return pad_right(computed_str.upper(), _STATUS_WIDTH)
    return pad_right(status_str.upper(), _STATUS_WIDTH)


# ---------------------------------------------------------------------------
# Table renderer
# ---------------------------------------------------------------------------

def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[int],
    *,
    divider: bool = True,
) -> str:
    """
    Render a fixed-width ASCII table.
    """
    n = len(headers)
    lines: List[str] = []

    def _row_str(cells: Sequence[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            w = col_widths[i] if i < len(col_widths) else 20
            parts.append(pad_right(truncate(str(cell), w), w))
        return "  ".join(parts).rstrip()

    lines.append(_row_str(headers))
    if divider:
        div_parts = ["-" * col_widths[i] for i in range(n)]
        lines.append("  ".join(div_parts))
    for row in rows:
        lines.append(_row_str(row))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Task-specific formatters
# ---------------------------------------------------------------------------

def format_task_row(
    task_id: int,
    priority_str: str,
    status_str: str,
    title: str,
    due_str: str = "-",
    computed_str: Optional[str] = None,
) -> str:
    """
    Return a single task summary line.
    """
    id_col       = pad_left(format_id(task_id), _ID_WIDTH)
    priority_col = format_priority(priority_str)
    status_col   = format_status(status_str, computed_str)
    title_col    = pad_right(truncate(title, 42), 42)
    due_col      = due_str

    return f"{id_col}  {priority_col}  {status_col}  {title_col}  {due_col}"


def format_task_header() -> str:
    """Return the column header line matching format_task_row."""
    id_col       = pad_left("ID", _ID_WIDTH)
    priority_col = pad_right("PRIORITY", _PRIORITY_WIDTH)
    status_col   = pad_right("STATUS", _STATUS_WIDTH)
    title_col    = pad_right("TITLE", 42)
    due_col      = "DUE"
    return f"{id_col}  {priority_col}  {status_col}  {title_col}  {due_col}"


def format_task_divider() -> str:
    """Return divider matching format_task_header."""
    return (
        "-" * _ID_WIDTH
        + "  " + "-" * _PRIORITY_WIDTH
        + "  " + "-" * _STATUS_WIDTH
        + "  " + "-" * 42
        + "  " + "-" * 16
    )


# ---------------------------------------------------------------------------
# Dependency graph ASCII art
# ---------------------------------------------------------------------------

def render_graph_ascii(
    tasks: dict,          # {id: title}
    edges: list,          # [(task_id, depends_on_id), ...]
    topo_order: list,     # [id, ...] in execution order
) -> str:
    """
    Render a clean ASCII dependency graph.
    """
    if not tasks:
        return "(no tasks)"

    # Build level mapping
    depends_on: dict = {}  # task_id -> set of dep ids
    for (tid, dep) in edges:
        depends_on.setdefault(tid, set()).add(dep)

    levels: dict = {}
    for tid in topo_order:
        deps = depends_on.get(tid, set())
        if not deps:
            levels[tid] = 0
        else:
            levels[tid] = max(levels.get(d, 0) for d in deps) + 1

    max_level = max(levels.values()) if levels else 0

    lines = []
    for lvl in range(max_level + 1):
        lvl_tasks = [tid for tid in topo_order if levels.get(tid, 0) == lvl]
        if not lvl_tasks:
            continue

        prefix = "  " * lvl
        for tid in lvl_tasks:
            title = tasks.get(tid, f"Task #{tid}")
            node = f"{prefix}#{tid} {title}"
            lines.append(node)

            # Draw arrows to tasks that depend on this one
            children = [
                t for t in topo_order
                if tid in depends_on.get(t, set()) and levels.get(t, 0) == lvl + 1
            ]
            if children:
                for child in children:
                    lines.append(f"{prefix}  |")
                lines.append(f"{prefix}  v")

    return "\n".join(lines) if lines else "(no tasks)"
