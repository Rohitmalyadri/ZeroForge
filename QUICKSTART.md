# ZeroForge — Quick Start Guide

Welcome to **ZeroForge**, the zero-runtime-dependency local task engine.

---

## 1. Quick Start on Windows

### Method A: One-Click / Terminal Launcher (`run.bat`)

1. **Extract** `ZeroForge.zip` to any folder on your computer.
2. Open **Command Prompt** or **PowerShell** in the extracted folder (or double-click `run.bat`).
3. Run:
   ```cmd
   run.bat
   ```
4. Choose your preferred interface:
   - `1` — Command Line Guide
   - `2` — Interactive REPL
   - `3` — Guided Wizard
   - `4` — Exit

You can also pass commands directly:
```cmd
run.bat repl
run.bat wizard
run.bat add "Design Database" --priority high
run.bat ready
run.bat plan
```

### Method B: Direct Python Command

```cmd
python -m zeroforge
```

---

## 2. Quick Start on macOS / Linux

1. **Extract** the release archive.
2. Open a terminal in the folder:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
   Or run directly with Python:
   ```bash
   python3 -m zeroforge
   ```

---

## 3. The 3 Interfaces

### 1. Guided Wizard (Beginner-Friendly)
```bash
python -m zeroforge wizard
```
Step-by-step numbered menus for creating tasks with natural language dates (`tomorrow`, `next friday`, `in 3 days`), completing tasks, and inspecting plans without memorizing CLI flags.

### 2. Interactive REPL (Power User Shell)
```bash
python -m zeroforge repl
```
Fast continuous terminal shell with command history (up/down arrows), tab completion, command aliases (`ls`, `rm`, `q`), and fuzzy task matching (e.g. `done db` finds and completes "Design Database").

### 3. Direct CLI (Scriptable & Fast)
```bash
python -m zeroforge add "Design DB" --priority high
python -m zeroforge add "Build API" --priority critical --after 1
python -m zeroforge ready
python -m zeroforge done 1
python -m zeroforge plan
python -m zeroforge graph
python -m zeroforge health
python -m zeroforge --version
```

---

## 4. Verification & Health Check

You can verify that your ZeroForge installation is functioning and has zero third-party dependencies:

```bash
# Run application health check
python -m zeroforge health

# Verify version
python -m zeroforge version

# Run the 92-test automated suite
python -m unittest discover tests
```

---

## 5. Requirements & Zero-Dependency Guarantee

- **Python 3.9+** (Standard Library only)
- **Zero Third-Party Dependencies** — No `pip install` required.

