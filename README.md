# ZeroForge

> **A zero-dependency local task engine that understands dependencies, constraints, priorities, and deadlines to determine what you can work on next.**

Built for the **Zero Dependency 2026 — 72-Hour Hackathon**.

[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20runtime-brightgreen.svg)](#zero-dependency-proof)
[![Standard Library](https://img.shields.io/badge/python-3.9%2B%20stdlib%20only-blue.svg)](#standard-library-substitutions)
[![License: MIT](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## 1. The Core Problem

Traditional Todo and Task applications answer:
> *"What tasks do I have?"*

In real software engineering projects, tasks are rarely isolated. They form a **directed acyclic graph (DAG)**:

```
Design Database ──► Build API ──► Write Tests ──► Deploy
```

If `Build API` depends on `Design Database`, you cannot start `Build API` while `Design Database` is `PENDING`.

ZeroForge answers:
> ***"Given my tasks, dependencies, deadlines, priorities, and constraints, what can I actually work on right now?"***

---

## 2. Key Features

- **Dependency Graph Engine**: Custom DFS cycle detection (WHITE/GRAY/BLACK node coloring) and Kahn's algorithm for topological sorting.
- **Dynamic Derived Readiness**: Tasks automatically compute `READY` vs `BLOCKED` states at runtime without stale state flags in the database.
- **Deterministic Scheduling**: Multi-key deterministic ranking algorithm that balances priority, deadline urgency, overdue status, and task age without starvation.
- **SQLite Persistence**: Embedded ACID-compliant relational storage with foreign keys and automatic cascade deletion.
- **Cycle Prevention**: Live graph inspection prevents direct and indirect dependency cycles before committing changes.
- **Terminal Visualization**: Pure ASCII DAG visualization for terminal environments.
- **Interactive REPL**: Shell with command history, tab completion, fuzzy task matching (e.g., `done db` finds "Design Database").
- **Guided Wizard**: Step-by-step menu-driven interface for new users with natural language date parsing.
- **Zero Third-Party Dependencies**: 100% Python standard library. No `click`, `rich`, `networkx`, `pydantic`, `sqlalchemy`, or `pytest`.

---

## 3. Quick Start & Launchers

### Quick Start (Windows)

Double-click `run.bat` or run from Command Prompt / PowerShell:

```cmd
run.bat
```

### Quick Start (macOS / Linux)

```bash
./run.sh
# or
python3 -m zeroforge
```

### Direct Launcher with Interface Selector

Running ZeroForge without arguments launches the **Initial Interface Selector**:

```bash
python -m zeroforge
```

```text
============================================================
ZEROFORGE
Dependency-Aware Task Engine
============================================================

Choose an interface:

  1. Command Line
     Run individual ZeroForge commands.

  2. Interactive REPL
     Work continuously inside ZeroForge.

  3. Guided Wizard
     Manage tasks through a guided interface.

  4. Exit

Select an option [1-4]:
```

---

### Three Ways to Use ZeroForge

**Option 1: Guided Wizard** (Recommended for new users)

```bash
python -m zeroforge wizard
```

The wizard provides a friendly, step-by-step interface:

```
╔══════════════════════════════════════════╗
║     ZeroForge Guided Wizard              ║
║     Step-by-step task management         ║
╚══════════════════════════════════════════╝

  What would you like to do?
    1. Create a new task
    2. View my tasks
    3. Complete a task
    4. See what I should work on
    5. View dependency graph
    6. Exit the wizard
```

Create tasks using natural language dates:
```
  Deadline: tomorrow, next friday, in 7 days, or 2026-09-15
```

**Option 2: Interactive REPL** (Power user mode)

```bash
python -m zeroforge repl
```

```
zf > add Design Database --priority high
[OK] Created task #1: Design Database
   Priority  : HIGH

zf > add Build API --priority critical --after 1
[OK] Created task #2: Build API

zf > ready
  #1  HIGH      READY        Design Database

zf > done db   ← Fuzzy matching!
[OK] Completed task #1: Design Database
  Tasks now ready:
    #2  CRITICAL  Build API
```

Features:
- Command history (up/down arrows)
- Tab completion
- Aliases: `ls` = `list`, `rm` = `delete`, `q` = `quit`
- Fuzzy task search: `done db` finds "Design Database"

**Option 3: Direct Commands** (Scriptable)

```bash
python -m zeroforge add "Design Database" --priority high
python -m zeroforge add "Build API" --priority critical --after 1
python -m zeroforge add "Write Tests" --priority high --after 2
python -m zeroforge add "Deploy" --priority critical --after 3
python -m zeroforge ready
python -m zeroforge plan
python -m zeroforge graph
```

---

## 4. Core Workflow Demo

```bash
# 1. Create tasks with priorities and dependencies
python -m zeroforge add "Design Database" --priority high
python -m zeroforge add "Build API" --priority critical --after 1
python -m zeroforge add "Write Tests" --priority high --after 2
python -m zeroforge add "Deploy" --priority critical --after 3

# 2. Inspect what is immediately actionable (only Design Database is READY)
python -m zeroforge ready

# 3. View what is currently blocked and why
python -m zeroforge blocked

# 4. View dependency graph
python -m zeroforge graph

# 5. Generate complete execution plan
python -m zeroforge plan

# 6. Complete task #1 and see task #2 unlock automatically
python -m zeroforge done 1
python -m zeroforge ready

# 7. Cycle protection demonstration (attempting Deploy -> Database cycle)
python -m zeroforge dep add 1 --on 4
# Output: ERROR: Dependency cycle detected: #1 -> #4 -> #3 -> #2 -> #1
```

---

## 5. Architecture Overview

```
                      +-------------------------+
                      |       CLI Parser        |  (argparse)
                      +------------+------------+
                                   |
                      +------------v------------+
                      |     Core Engine         |  (Business Orchestration)
                      +---+--------+--------+---+
                          |        |        |
        +-----------------+        |        +-----------------+
        |                          |                          |
+-------v-------+          +-------v-------+          +-------v-------+
|  Dependency   |          |   Scheduler   |          | SQLite Store  |
|  Graph Engine |          |  (Multi-Key)  |          | (sqlite3 WAL) |
+---------------+          +---------------+          +---------------+

Optional UI Layers:
+-------v-------+          +-------v-------+
|  Interactive  |          |   Guided      |
|  REPL Shell   |          |   Wizard      |
+---------------+          +---------------+
```

For complete technical specifications, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 6. Standard Library Substitutions

| External Package | ZeroForge Stdlib Replacement | Purpose |
|---|---|---|
| `click` / `typer` | `argparse` | CLI commands, options, help text |
| `sqlalchemy` / `peewee` | `sqlite3` + parameterization | ACID relational persistence with foreign keys |
| `networkx` | `core/dependency.py` (custom graph) | DFS cycle detection & Kahn's topo sort |
| `pydantic` | `dataclasses` + `core/validator.py` | Schema validation and domain models |
| `rich` / `tabulate` | `utils/formatting.py` | Fixed-width table alignment & ASCII graph rendering |
| `pytest` | `unittest` | Complete 92-test unit, edge-case & integration test suite |
| `python-dateutil` | `datetime` | Timezone-aware UTC timestamps & ISO-8601 parsing |
| `apscheduler` | `core/scheduler.py` | Multi-key priority & deadline ranking engine |
| `IPython` / `prompt_toolkit` | `cli/repl.py` (readline) | Interactive shell with history & completion |
| `fuzzywuzzy` / `rapidfuzz` | `cli/repl.py` (custom) | Fuzzy task matching & resolution |
| `dateparser` / `humanize` | `cli/wizard.py` (datetime) | Natural language date parsing |

Detailed replacement analysis: [STDLIB.md](STDLIB.md).

---

## 7. Application Health Check

Verify your environment, database, graph algorithms, and interface modules at any time:

```bash
python -m zeroforge health
```

```text
============================================================
                 ZEROFORGE HEALTH CHECK
============================================================

  Environment
    [OK]    Python Version (>= 3.9)      v3.13.8
    [OK]    Runtime Dependencies         0 third-party (100% stdlib)

  Core Components
    [OK]    Database & Migrations        SQLite WAL mode + Foreign keys initialized
    [OK]    Task Storage (CRUD)          CRUD & cascade operations verified
    [OK]    Dependency Graph             3-Color DFS cycle prevention & topological sort verified
    [OK]    Planner / Scheduler          5-key deterministic multi-tier ranking verified

  User Interfaces
    [OK]    CLI Interface                Argparse command parser verified
    [OK]    Interactive REPL             REPL commands, token parser & fuzzy search ready
    [OK]    Guided Wizard                Guided wizard & natural date parser ready

------------------------------------------------------------
  Overall Status: HEALTHY
------------------------------------------------------------
```

The health check executes in an isolated temporary database and is guaranteed **100% non-destructive** to your tasks.

---

## 8. Version Information

```bash
python -m zeroforge --version
# or
python -m zeroforge version
```
Output:
```text
ZeroForge v1.0.0
```

---

## 9. Running Tests

```bash
python -m unittest discover tests
```

---

## 10. Zero-Dependency Proof

You can verify that no third-party runtime packages are imported or required:

```bash
# Verify clean import in an isolated virtualenv without site-packages
python -c "import zeroforge; print('ZeroForge runs with 0 third-party dependencies!')"
```

---

## 11. License

MIT License. See [LICENSE](LICENSE) for details.

