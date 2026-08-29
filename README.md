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

## 3. Quick Start & Demo Flow

### Installation & Execution (Zero Setup)

ZeroForge requires only Python 3.9+ with no `pip install`:

```bash
# Check version
python -m zeroforge --version

# View help
python -m zeroforge --help
```

### Complete 2-Minute Walkthrough

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

### Interactive Modes

ZeroForge also provides two interactive interfaces for a better user experience:

```bash
# Interactive REPL shell (with history, tab completion, fuzzy matching)
python -m zeroforge repl
# Example: "done db" finds and marks "Design Database" as done

# Guided wizard (step-by-step, menu-driven)
python -m zeroforge wizard
```

---

## 4. Architecture Overview

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
```

For complete technical specifications, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 5. Standard Library Substitutions

| External Package | ZeroForge Stdlib Replacement | Purpose |
|---|---|---|
| `click` / `typer` | `argparse` | CLI commands, options, help text |
| `sqlalchemy` / `peewee` | `sqlite3` + parameterization | ACID relational persistence with foreign keys |
| `networkx` | `core/dependency.py` (custom graph) | DFS cycle detection & Kahn's topo sort |
| `pydantic` | `dataclasses` + `core/validator.py` | Schema validation and domain models |
| `rich` / `tabulate` | `utils/formatting.py` | Fixed-width table alignment & ASCII graph rendering |
| `pytest` | `unittest` | Complete 35-test unit & integration test suite |
| `python-dateutil` | `datetime` | Timezone-aware UTC timestamps & ISO-8601 parsing |
| `apscheduler` | `core/scheduler.py` | Multi-key priority & deadline ranking engine |

Detailed replacement analysis: [STDLIB.md](STDLIB.md).

---

## 6. Running Tests

```bash
python -m unittest discover tests
```

---

## 7. Zero-Dependency Proof

You can verify that no third-party runtime packages are imported or required:

```bash
# Verify clean import in an isolated virtualenv without site-packages
python -c "import zeroforge; print('ZeroForge runs with 0 third-party dependencies!')"
```

---

## 8. License

MIT License. See [LICENSE](LICENSE) for details.
