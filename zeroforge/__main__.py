"""
zeroforge/__main__.py
~~~~~~~~~~~~~~~~~~~~~
Main entry point for ZeroForge CLI application.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure standard output/error handle encoding gracefully on all operating systems
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the root project directory is on sys.path so modules can be imported directly
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from cli.parser import build_parser, VERSION
from cli.commands import dispatch
from cli.selector import run_selector
from core.engine import Engine
from storage.database import Database
from utils.errors import StorageError


def get_default_db_path() -> Path:
    """
    Resolve default SQLite database path.
    Can be overridden via ZEROFORGE_DB environment variable.
    """
    env_path = os.environ.get("ZEROFORGE_DB")
    if env_path:
        return Path(env_path)
    return Path.home() / ".zeroforge" / "tasks.db"


def main(argv: list[str] | None = None) -> int:
    """CLI application entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    # Determine database path
    db_path = Path(args.db) if args.db else get_default_db_path()

    try:
        db = Database(db_path)
        db.initialize()
    except StorageError as exc:
        print(f"ERROR: Database initialization failed: {exc}", file=sys.stderr)
        return 1

    # If no sub-command provided, launch the Initial Interface Selector
    if not args.command:
        return run_selector(db, parser)

    try:
        engine = Engine(db)
        return dispatch(engine, args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"ERROR: Unexpected runtime error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())