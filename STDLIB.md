# Standard Library Substitutions in ZeroForge

ZeroForge was designed for the **Zero Dependency 2026 Hackathon**. This document provides an audit of every third-party package commonly used in Python task/graph applications and explains the stdlib substitution built for ZeroForge.

---

### 1. `click` / `typer` ➔ `argparse`
- **Module**: `cli/parser.py`, `zeroforge/__main__.py`
- **Technique**: Configured nested subparsers (`add`, `list`, `show`, `update`, `delete`, `start`, `done`, `cancel`, `dep`, `ready`, `blocked`, `plan`, `graph`) with clean option typing, custom help formatting, and exit code routing.

### 2. `sqlalchemy` / `peewee` ➔ `sqlite3`
- **Module**: `storage/database.py`, `storage/migrations.py`
- **Technique**: Parameterized SQL queries, WAL journal mode, explicit foreign key enforcement (`PRAGMA foreign_keys = ON`), schema version tracking, and `ON DELETE CASCADE` edge cleanup.

### 3. `networkx` ➔ Custom Graph Algorithms (`core/dependency.py`)
- **Module**: `core/dependency.py`
- **Technique**:
  - **Cycle Detection**: Depth-First Search with 3-color vertex marking (`WHITE=0, GRAY=1, BLACK=2`) providing $O(V + E)$ cycle detection and explicit path reconstruction for diagnostics.
  - **Topological Sorting**: Kahn's algorithm using in-degree calculation and queue determinism.
  - **Ancestorship / Transitive Closure**: Graph traversal over dependency adjacencies.

### 4. `pydantic` ➔ `dataclasses` + Custom Validators (`core/models.py`, `core/validator.py`)
- **Module**: `core/models.py`, `core/validator.py`
- **Technique**: Python `dataclass` instances combined with strict type coercion and business rule validators for title length, enum constraints, positive integer bounds, and ISO-8601 timestamps.

### 5. `rich` / `tabulate` ➔ Terminal Formatter (`utils/formatting.py`)
- **Module**: `utils/formatting.py`
- **Technique**: Fixed-width column calculation, text truncation with ellipsis, cross-platform ASCII table dividers, status tags, and multi-level ASCII graph rendering.

### 6. `pytest` ➔ `unittest`
- **Module**: `tests/`
- **Technique**: Comprehensive test suite with test fixtures (`setUp`, `tearDown`, `tempfile.TemporaryDirectory`) covering unit and end-to-end CLI integration.

### 7. `python-dateutil` ➔ `datetime` (`utils/dates.py`)
- **Module**: `utils/dates.py`
- **Technique**: Robust multi-format parsing for ISO-8601 strings, UTC timezone normalization, end-of-day deadline expansion, and deadline urgency scoring.

### 8. `apscheduler` ➔ Deterministic Scheduling Engine (`core/scheduler.py`)
- **Module**: `core/scheduler.py`
- **Technique**: Multi-key sort tuple `(-priority_weight, overdue_flag, urgency_seconds, created_timestamp, task_id)` ensuring strict determinism and anti-starvation.

### 9. `IPython` / `prompt_toolkit` ➔ Interactive REPL (`cli/repl.py`)
- **Module**: `cli/repl.py`
- **Technique**: Readline-backed shell with command history persistence, Tab completion dispatcher, alias resolution (e.g. `ls` for `list`, `rm` for `delete`), fuzzy task matching using substring + exact-title preference, and a shell-style tokenizer that respects quoted strings.

### 10. `fuzzywuzzy` / `rapidfuzz` ➔ Stdlib Fuzzy Matching (`cli/repl.py`)
- **Module**: `cli/repl.py`
- **Technique**: Two-stage resolution — first try exact title match, then pick the shortest title containing the query as a substring. This replaces common fuzzy-search libraries while keeping the implementation readable.

### 11. `dateparser` / `humanize` ➔ Natural Language Dates (`cli/wizard.py`)
- **Module**: `cli/wizard.py`
- **Technique**: Pure stdlib date parser for human-friendly expressions: `today`, `tomorrow`, `yesterday`, `in N days`, `next <day>`, plus ISO-8601 fallback. Uses only `datetime` and `timedelta` — no external library.
