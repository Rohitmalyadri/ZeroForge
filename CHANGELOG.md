# Changelog

All notable changes to ZeroForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-29

### Added
- **Initial Interface Selector**: Interactive terminal menu launched when running `python -m zeroforge` without arguments, offering direct choice between CLI guide, REPL, Wizard, and Exit.
- **Portable Windows Launcher (`run.bat`)**: Seamless zero-configuration startup script with Python environment detection and path-safety across Command Prompt and PowerShell.
- **Portable Unix Launcher (`run.sh`)**: Executable shell launcher for macOS and Linux environments.
- **Guided Wizard (`cli/wizard.py`)**: Step-by-step numbered menu workflow with natural language date parsing (`today`, `tomorrow`, `next friday`, `in 7 days`).
- **Interactive REPL (`cli/repl.py`)**: Continuous shell with persistent command history, tab completion, command aliases (`ls`, `rm`, `q`), and fuzzy task matching (`done db`).
- **Core Dependency Engine (`core/dependency.py`)**: 3-Color DFS cycle detection ($O(V+E)$), Kahn's topological sort, and runtime derived `READY`/`BLOCKED` status determination.
- **Deterministic Scheduler (`core/scheduler.py`)**: 5-key multi-tier priority & deadline ranking engine preventing task starvation.
- **SQLite Persistence (`storage/database.py`)**: Embedded ACID relational storage with foreign key enforcement and `ON DELETE CASCADE` edge handling.
- **Application Health Check (`core/health.py`)**: Built-in non-destructive environment and component verification (`python -m zeroforge health`).
- **Version Subcommand and Standard Flag**: Support for `python -m zeroforge --version` and `python -m zeroforge version` with single source of truth in `zeroforge/__init__.py`.
- **Quickstart Guide (`QUICKSTART.md`)**: Getting started guide for Windows, macOS, and Linux users.
- **Comprehensive Test Suite (`tests/`)**: 92 unit, integration, and edge-case test cases covering models, validators, graph algorithms, scheduler, storage, REPL, wizard, health check, and interface selector.

