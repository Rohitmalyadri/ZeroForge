# ZeroForge Architecture

## 1. System Design

ZeroForge follows a layered architecture with separation of concerns:

```
zeroforge/
├── cli/          # CLI interface (parser, commands, REPL, wizard)
├── core/         # Core business logic (models, validation, dependency graph, scheduler, engine)
├── storage/      # SQLite persistence, migrations, and transactions
└── utils/        # Error hierarchy, date calculations, ASCII formatting
```

### Module Responsibilities

1. **CLI Layer (`cli/`)**:
   - **parser.py**: Parses arguments via standard library `argparse`.
   - **commands.py**: Routes parsed commands to engine methods, formats output.
   - **repl.py**: Interactive shell with history, completion, and fuzzy matching.
   - **wizard.py**: Step-by-step menu-driven interface for new users.
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

### Command-Line Mode

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

### Interactive Modes

```
                    ┌──────────────┐
                    │   User       │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        [cli/repl.py]            [cli/wizard.py]
     Interactive Shell         Guided Menus
              │                         │
              └────────────┬────────────┘
                           ▼
                    [cli/commands.py]
                           │
                           ▼
                    [core/engine.py]
                           │
                           ▼
                  [storage/database.py]
```

Both interactive modes (REPL and Wizard) eventually call into the same `core/engine.py` business logic. They differ only in how they collect user input and present output:

- **REPL**: Accepts text commands, parses them, and routes to the engine
- **Wizard**: Presents numbered menus and prompts, collecting inputs step by step

---

## 3. Interactive Modes

### REPL (`cli/repl.py`)

The Read-Eval-Print-Loop provides a Unix shell-like experience:

- **Command Registry**: 15 commands with aliases (e.g., `ls` = `list`, `rm` = `delete`)
- **History**: Uses `readline` for command history with persistence
- **Tab Completion**: Completes command names and aliases
- **Fuzzy Matching**: `done db` resolves to task containing "db" in title
- **Shell Escape**: `!ls` runs system commands
- **Tokenizer**: Respects quoted strings (`add "My task" --priority high`)

**Entry point**: `python -m zeroforge repl`

### Wizard (`cli/wizard.py`)

A guided, menu-driven interface for users unfamiliar with CLI tools:

- **Menu-Driven**: Numbered choices for each action
- **Step-by-Step**: Prompts for each field when creating tasks
- **Natural Language Dates**: Accepts `tomorrow`, `next friday`, `in 7 days`
- **Summary Before Commit**: Shows task details before creation
- **Confirmation Prompts**: Prevents accidental operations

**Available workflows**:
1. Create a new task (with all fields)
2. View tasks by status
3. Complete a task (guided selection)
4. See execution plan
5. View dependency graph

**Entry point**: `python -m zeroforge wizard`

---

## 4. Why No LLM?

ZeroForge's interactive modes use pattern matching and natural language parsing, not a Large Language Model. This is a deliberate design decision:

1. **Zero Network Dependency**: Works offline, no API calls
2. **Deterministic**: Same input always produces same output
3. **Fast**: No latency from API round-trips
4. **Cost-Free**: No API key or usage costs
5. **Hackathon Theme**: Demonstrates stdlib alternatives to LLM-powered tools

The wizard's natural language date parser is a simple but useful demonstration of how stdlib `datetime` can replace libraries like `dateparser` for common use cases.
