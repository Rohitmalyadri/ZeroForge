"""
cli/selector.py
~~~~~~~~~~~~~~~
Initial interface selector for ZeroForge.

Provides a clean, friendly menu when ZeroForge is launched with no arguments:
  1. Command Line (CLI help and overview)
  2. Interactive REPL
  3. Guided Wizard
  4. Exit

Uses only Python standard library.
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from storage.database import Database
from cli.repl import run_repl
from cli.wizard import run_wizard
from utils.formatting import section_header


def _show_menu() -> None:
    """Render the main interface selection menu."""
    print()
    print(section_header("ZEROFORGE\nDependency-Aware Task Engine"))
    print()
    print("  Choose an interface:")
    print()
    print("    1. Command Line")
    print("       Run individual ZeroForge commands.")
    print()
    print("    2. Interactive REPL")
    print("       Work continuously inside ZeroForge.")
    print()
    print("    3. Guided Wizard")
    print("       Manage tasks through a guided interface.")
    print()
    print("    4. Exit")
    print()


def _handle_cli_choice(parser: Optional[argparse.ArgumentParser]) -> None:
    """Display CLI overview and command reference."""
    print()
    print("=" * 60)
    print("COMMAND LINE INTERFACE (CLI)")
    print("=" * 60)
    print()
    print("  ZeroForge CLI commands can be run directly from your terminal:")
    print()
    print("    python -m zeroforge add \"Task title\" --priority high")
    print("    python -m zeroforge add \"Next task\" --after 1")
    print("    python -m zeroforge list")
    print("    python -m zeroforge ready")
    print("    python -m zeroforge done 1")
    print("    python -m zeroforge plan")
    print("    python -m zeroforge graph")
    print("    python -m zeroforge health")
    print("    python -m zeroforge --version")
    print()
    if parser is not None:
        print("  Available Commands & Options:")
        print("  " + "-" * 56)
        parser.print_help()
    print()
    try:
        input("  Press Enter to return to the main menu...")
    except (EOFError, KeyboardInterrupt):
        print()


def run_selector(db: Database, parser: Optional[argparse.ArgumentParser] = None) -> int:
    """
    Run the interactive interface selector loop.

    Parameters
    ----------
    db : Database
        Initialized SQLite database instance.
    parser : Optional[argparse.ArgumentParser]
        CLI parser for showing help when Option 1 is selected.

    Returns
    -------
    int
        Exit code (0 on normal exit).
    """
    while True:
        _show_menu()

        try:
            choice = input("  Select an option [1-4]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            return 0

        if not choice:
            print("\n  Please enter a choice (1-4).")
            continue

        choice_lower = choice.lower()

        if choice_lower in ("4", "exit", "quit", "q"):
            print("\n  Goodbye!")
            return 0

        elif choice_lower in ("1", "cli", "command", "command line"):
            _handle_cli_choice(parser)
            continue

        elif choice_lower in ("2", "repl", "interactive"):
            try:
                run_repl(db)
            except (EOFError, KeyboardInterrupt):
                print()
            continue

        elif choice_lower in ("3", "wizard", "guide"):
            try:
                run_wizard(db)
            except (EOFError, KeyboardInterrupt):
                print()
            continue

        else:
            print(f"\n  Invalid selection '{choice}'.")
            print("  Please choose an option between 1 and 4, or type 'exit'.")
            continue
