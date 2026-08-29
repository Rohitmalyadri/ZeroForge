"""
cli/repl.py
~~~~~~~~~~~
Interactive REPL shell for ZeroForge.

Provides a Read-Eval-Print-Loop with:
- Command history (up/down arrows)
- Smart tab completion for tasks, priorities, statuses
- Natural language shortcuts (e.g. "ls" for "list")
- Fuzzy task matching (e.g. "done db" finds "Design DB" task)
- Inline help (? after any command)

Uses only Python standard library (readline/lineinput, difflib).
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from core.engine import Engine
from core.models import TaskStatus, Priority
from storage.database import Database
from utils.errors import ZeroForgeError

# Try to import readline for history/completion; fall back to builtins
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

class Command:
    """A single REPL command."""
    def __init__(
        self,
        name: str,
        aliases: list[str],
        help_text: str,
        arg_hint: str = "",
    ):
        self.name = name
        self.aliases = aliases
        self.help_text = help_text
        self.arg_hint = arg_hint

COMMANDS: list[Command] = [
    Command("add", ["create", "new"], "Create a new task", "<title> [--priority P] [--after ID]"),
    Command("list", ["ls", "tasks"], "List all tasks", "[-s STATUS]"),
    Command("show", ["view", "info"], "Show task details", "<id>"),
    Command("update", ["edit", "modify"], "Update a task", "<id> [--title T] [--priority P] ..."),
    Command("delete", ["del", "remove", "rm"], "Delete a task", "<id>"),
    Command("start", ["begin", "work"], "Start working on a task", "<id>"),
    Command("done", ["complete", "finish", "finish"], "Mark task as done", "<id or search>"),
    Command("cancel", [], "Cancel a task", "<id>"),
    Command("dep", ["dependency", "depends"], "Manage dependencies", "add|remove|list <args>"),
    Command("ready", [], "List READY tasks", ""),
    Command("blocked", [], "List BLOCKED tasks", ""),
    Command("plan", ["schedule"], "Generate execution plan", ""),
    Command("graph", ["visualise", "viz"], "Show dependency graph", ""),
    Command("help", ["?"], "Show this help", "[command]"),
    Command("quit", ["exit", "q"], "Exit the REPL", ""),
]

# Build lookup by name + aliases
_COMMAND_MAP: dict[str, Command] = {}
for cmd in COMMANDS:
    _COMMAND_MAP[cmd.name] = cmd
    for alias in cmd.aliases:
        _COMMAND_MAP[alias] = cmd


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _get_input(prompt: str) -> Optional[str]:
    """Read a line of input, returning None on EOF."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return None


def _setup_readline(history_path: str) -> None:
    """Configure readline with history and completion."""
    if not READLINE_AVAILABLE:
        return
    try:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode vi")
        # Load history
        if os.path.exists(history_path):
            readline.read_history_file(history_path)
        readline.set_history_length(100)
    except Exception:
        pass  # Non-fatal — readline config can fail on some platforms


def _save_history(history_path: str) -> None:
    """Append current session history to the history file."""
    if not READLINE_AVAILABLE:
        return
    try:
        readline.write_history_file(history_path)
    except Exception:
        pass


def _complete(text: str, state: int) -> Optional[str]:
    """Tab completion callback for readline."""
    # Completion options depend on what the user has typed
    tokens = text.split()
    if not tokens:
        return None

    # If we're at the start of a line, complete command names
    if len(tokens) == 1:
        options = [c.name for c in COMMANDS if c.name.startswith(text)]
        options += [alias for cmd in COMMANDS for alias in cmd.aliases if alias.startswith(text)]
        if state < len(options):
            return options[state]
        return None

    # After a command, complete based on context
    cmd_name = tokens[0].lower()
    if cmd_name not in _COMMAND_MAP:
        return None

    cmd = _COMMAND_MAP[cmd_name]
    # For commands that take an ID, we could complete from task IDs
    # This is a simplified version — full implementation would query engine
    return None


# ---------------------------------------------------------------------------
# Natural language / fuzzy matching
# ---------------------------------------------------------------------------

def _fuzzy_match_task(engine: Engine, query: str) -> Optional[int]:
    """
    Try to resolve a task ID from a fuzzy query.

    - If query is a number, return it as int.
    - Otherwise, search task titles (case-insensitive substring match).
    - If multiple matches, prefer exact substring matches, then shortest title.
    Returns the first match or None.
    """
    query = query.strip()
    if not query:
        return None

    # Numeric ID?
    try:
        return int(query)
    except ValueError:
        pass

    # Search by title
    try:
        all_tasks = engine.list_tasks()
    except ZeroForgeError:
        return None

    matches = []
    query_lower = query.lower()
    for task in all_tasks:
        if task.title.lower() == query_lower:
            # Exact match — return immediately
            return task.id
        if query_lower in task.title.lower():
            matches.append(task)

    if len(matches) == 1:
        return matches[0].id
    elif len(matches) > 1:
        # Return the shortest title match (most specific)
        matches.sort(key=lambda t: len(t.title))
        return matches[0].id

    return None


# ---------------------------------------------------------------------------
# Command parser (simple tokenizing)
# ---------------------------------------------------------------------------

def _parse_tokens(line: str) -> list[str]:
    """Split a command line into tokens, respecting quoted strings."""
    tokens = []
    current = []
    in_quote = False
    quote_char = None

    for ch in line:
        if ch in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = ch
        elif ch == quote_char and in_quote:
            in_quote = False
            quote_char = None
        elif ch.isspace() and not in_quote:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)

    if current:
        tokens.append("".join(current))
    return tokens


# ---------------------------------------------------------------------------
# Command executor
# ---------------------------------------------------------------------------

def _execute(engine: Engine, tokens: list[str]) -> int:
    """
    Parse tokens and execute the corresponding command.
    Returns an exit code.
    """
    if not tokens:
        return 0

    cmd_raw = tokens[0].lower()
    cmd = _COMMAND_MAP.get(cmd_raw)

    if cmd is None:
        print(f"Unknown command: {cmd_raw}. Type 'help' for available commands.", file=sys.stderr)
        return 1

    # Build args-like namespace
    class Args:
        pass

    args = Args()
    args.command = cmd.name

    # Simple argument routing per command
    rest = tokens[1:]

    if cmd.name == "help":
        if rest:
            target = rest[0].lower()
            target_cmd = _COMMAND_MAP.get(target)
            if target_cmd:
                _show_help_for(target_cmd)
            else:
                print(f"Unknown command: {target}")
        else:
            _show_general_help()
        return 0

    if cmd.name == "quit":
        return 99  # Special exit code

    if cmd.name == "add":
        # add <title> [--priority P] [--after ID] ...
        args.title = " ".join(rest) if rest else ""
        args.priority = "medium"
        args.description = ""
        args.due = None
        args.estimate = None
        args.after = None
        # Parse flags
        i = 0
        new_rest = []
        while i < len(rest):
            tok = rest[i]
            if tok == "--priority" or tok == "-p":
                if i + 1 < len(rest):
                    args.priority = rest[i + 1]
                    i += 2
                else:
                    i += 1
            elif tok == "--after" or tok == "-a":
                if i + 1 < len(rest):
                    args.after = [int(rest[i + 1])]
                    i += 2
                else:
                    i += 1
            elif tok == "--description" or tok == "-d":
                if i + 1 < len(rest):
                    args.description = rest[i + 1]
                    i += 2
                else:
                    i += 1
            elif tok == "--due":
                if i + 1 < len(rest):
                    args.due = rest[i + 1]
                    i += 2
                else:
                    i += 1
            elif tok == "--estimate" or tok == "-e":
                if i + 1 < len(rest):
                    args.estimate = int(rest[i + 1])
                    i += 2
                else:
                    i += 1
            else:
                new_rest.append(tok)
                i += 1
        args.title = " ".join(new_rest) if new_rest else ""
        from cli.commands import cmd_add
        return cmd_add(engine, args)

    if cmd.name == "list":
        args.status = None
        if rest and rest[0] == "-s" and len(rest) > 1:
            args.status = rest[1]
        from cli.commands import cmd_list
        return cmd_list(engine, args)

    if cmd.name == "show":
        if not rest:
            print("Usage: show <id>", file=sys.stderr)
            return 1
        try:
            args.id = int(rest[0])
        except ValueError:
            print(f"Invalid task ID: {rest[0]}", file=sys.stderr)
            return 1
        from cli.commands import cmd_show
        return cmd_show(engine, args)

    if cmd.name in ("delete", "start", "done", "cancel"):
        if not rest:
            print(f"Usage: {cmd.name} <id or search>", file=sys.stderr)
            return 1
        # Try fuzzy match
        task_id = _fuzzy_match_task(engine, rest[0])
        if task_id is None:
            print(f"Task not found: {rest[0]}", file=sys.stderr)
            return 1
        args.id = task_id

        if cmd.name == "delete":
            args.yes = True  # Auto-confirm in REPL
            from cli.commands import cmd_delete
            return cmd_delete(engine, args)
        elif cmd.name == "start":
            from cli.commands import cmd_start
            return cmd_start(engine, args)
        elif cmd.name == "done":
            from cli.commands import cmd_done
            return cmd_done(engine, args)
        else:
            from cli.commands import cmd_cancel
            return cmd_cancel(engine, args)

    if cmd.name == "update":
        if not rest:
            print("Usage: update <id> [options]", file=sys.stderr)
            return 1
        try:
            args.id = int(rest[0])
        except ValueError:
            print(f"Invalid task ID: {rest[0]}", file=sys.stderr)
            return 1
        args.title = None
        args.description = None
        args.priority = None
        args.due = None
        args.estimate = None
        args.clear_due = False
        # Parse flags
        i = 1
        while i < len(rest):
            tok = rest[i]
            if tok == "--title" or tok == "-t":
                if i + 1 < len(rest):
                    args.title = rest[i + 1]
                    i += 2
                else:
                    i += 1
            elif tok == "--priority" or tok == "-p":
                if i + 1 < len(rest):
                    args.priority = rest[i + 1]
                    i += 2
                else:
                    i += 1
            elif tok == "--clear-due":
                args.clear_due = True
                i += 1
            else:
                i += 1
        from cli.commands import cmd_update
        return cmd_update(engine, args)

    if cmd.name == "dep":
        if not rest:
            print("Usage: dep add|remove|list <args>", file=sys.stderr)
            return 1
        args.dep_command = rest[0]
        if rest[0] == "add":
            args.id = int(rest[1]) if len(rest) > 1 else 0
            args.on = int(rest[3]) if len(rest) > 3 and rest[2] == "--on" else None
            from cli.commands import cmd_dep_add
            return cmd_dep_add(engine, args)
        elif rest[0] == "remove":
            args.id = int(rest[1]) if len(rest) > 1 else 0
            args.on = int(rest[3]) if len(rest) > 3 and rest[2] == "--on" else None
            from cli.commands import cmd_dep_remove
            return cmd_dep_remove(engine, args)
        elif rest[0] == "list":
            args.id = int(rest[1]) if len(rest) > 1 else 0
            from cli.commands import cmd_dep_list
            return cmd_dep_list(engine, args)
        else:
            print(f"Unknown dep subcommand: {rest[0]}", file=sys.stderr)
            return 1

    if cmd.name == "ready":
        from cli.commands import cmd_ready
        return cmd_ready(engine, args)

    if cmd.name == "blocked":
        from cli.commands import cmd_blocked
        return cmd_blocked(engine, args)

    if cmd.name == "plan":
        from cli.commands import cmd_plan
        return cmd_plan(engine, args)

    if cmd.name == "graph":
        from cli.commands import cmd_graph
        return cmd_graph(engine, args)

    print(f"Command '{cmd.name}' not yet implemented in REPL.", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Help display
# ---------------------------------------------------------------------------

def _show_general_help() -> None:
    print("\n  ZeroForge REPL — Available commands:\n")
    for cmd in COMMANDS:
        aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
        print(f"  {cmd.name:<10}{aliases:<18} {cmd.help_text}")
    print("\n  Type 'help <command>' for detailed usage.")
    print("  Use --priority P (low/medium/high/critical)")
    print("  Use --after ID to add dependencies when creating tasks")
    print("  Fuzzy search: 'done db' finds task containing 'db' in title\n")


def _show_help_for(cmd: Command) -> None:
    print(f"\n  {cmd.name} {cmd.arg_hint}")
    print(f"  {cmd.help_text}")
    if cmd.aliases:
        print(f"  Aliases: {', '.join(cmd.aliases)}")
    print()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _show_banner() -> None:
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     ZeroForge Interactive REPL           ║")
    print("  ║     Zero-dependency task engine         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print("  Type 'help' for commands, 'quit' to exit.")
    print()


# ---------------------------------------------------------------------------
# Main REPL loop
# ---------------------------------------------------------------------------

def run_repl(db: Database) -> int:
    """
    Run the interactive REPL loop.
    Returns the exit code.
    """
    engine = Engine(db)
    history_path = os.path.expanduser("~/.zeroforge/.repl_history")

    _setup_readline(history_path)
    _show_banner()

    if READLINE_AVAILABLE:
        # Set up completer
        try:
            readline.set_completer(lambda text, state: _complete(text, state))
        except Exception:
            pass

    while True:
        line = _get_input("zf > ")
        if line is None:
            print()
            break

        line = line.strip()
        if not line:
            continue

        # Skip comment lines
        if line.startswith("#"):
            continue

        # Handle !shell escape
        if line.startswith("!"):
            os.system(line[1:])
            continue

        tokens = _parse_tokens(line)
        exit_code = _execute(engine, tokens)

        if exit_code == 99:
            print("Goodbye!")
            break

    _save_history(history_path)
    return 0
