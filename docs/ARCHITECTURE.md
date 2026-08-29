# ZeroForge Architecture

## 1. System Design

ZeroForge follows a layered architecture with separation of concerns:

```
zeroforge/
├── cli/          # CLI interface (parser, formatters, command dispatch)
├── core/         # Core business logic (models, validation, dependency graph, scheduler, engine)
├── storage/      # SQLite persistence, migrations, and transactions
└── utils/        # Error hierarchy, date calculations, ASCII formatting
```

### Module Responsibilities

1. **CLI Layer (`cli/`)**:
   - Parses arguments via standard library `argparse`.
   - Translates business exceptions into clean user error messages.
   - Enforces separation of `stdout` (data) and `stderr` (errors/warnings).
   - Never accesses `sqlite3` directly.

2. **Core Engine (`core/engine.py`)**:
   - Central orchestrator between the CLI and backend subsystems.
   - Coordinates domain models, database queries, dependency algorithms, and scheduler rankings.

3. **Dependency Engine (`core/dependency.py`)**:
   - Graph algorithms with zero dependencies.
   - Cycle detection via DFS vertex coloring.
   - Topological sorting via Kahn's algorithm.
   - Derives `READY` vs `BLOCKED` states without database mutation.

4. **Scheduler (`core/scheduler.py`)**:
   - Multi-key deterministic ranking algorithm.
   - Simulates wave-by-wave execution order.

5. **Storage Layer (`storage/database.py`)**:
   - SQLite persistence with `PRAGMA foreign_keys = ON`.
   - Automatic cascade deletion for dependency edges.
   - Schema version tracking via `storage/migrations.py`.

---

## 2. Data Flow

```
[User Input] ──► [cli/parser.py] ──► [cli/commands.py]
                                            │
                                            ▼
                                    [core/engine.py]
                                     /      |      \
                                    /       |       \
                                   ▼        ▼        ▼
                      [core/validator] [storage/db] [core/dependency]
                                                \    /
                                                 \  /
                                                  ▼
                                          [core/scheduler]
```
