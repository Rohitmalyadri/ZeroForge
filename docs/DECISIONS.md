# ZeroForge Architecture Decision Records (ADRs)

### ADR-001: Standard Library vs. Third-Party Dependencies
- **Context**: Hackathon requires zero third-party runtime dependencies.
- **Decision**: Use only standard library modules (`argparse`, `sqlite3`, `dataclasses`, `datetime`, `unittest`, `collections`).
- **Consequences**: Zero dependency risk, zero supply-chain attack surface, instant startup time, 100% portable installation.

### ADR-002: Derived Ready/Blocked State vs. Stored State
- **Context**: When a task's status or its dependencies change, cached readiness flags can become desynchronized.
- **Decision**: Derive `READY` and `BLOCKED` dynamically from the dependency graph and task statuses at query time.
- **Consequences**: Eliminates database synchronization bugs; guarantees correct state consistency.

### ADR-003: Cascade Delete vs. Dependent Protection on Task Deletion
- **Context**: When deleting a task that has incoming or outgoing dependency edges.
- **Decision**: Configure SQLite `ON DELETE CASCADE` on foreign key relations.
- **Consequences**: Deleting a task cleanly removes associated dependency edges without leaving dangling references or orphan foreign keys.

### ADR-004: Pure ASCII Formatting with Unicode Fallback
- **Context**: Windows terminal encoding vs. Linux/macOS UTF-8 environments.
- **Decision**: Use universal ASCII box drawing (`=`, `-`, `|`, `+--`, `->`) with stream encoding safety.
- **Consequences**: Guaranteed crash-free rendering across Windows cmd, PowerShell, and Unix terminals.
