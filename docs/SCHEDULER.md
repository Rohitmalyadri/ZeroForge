# ZeroForge Scheduler & Graph Algorithm Specification

## 1. Derived Readiness Model

In ZeroForge, `READY` and `BLOCKED` are **runtime derived states** rather than statically stored database fields.

A task $T$ is **READY** if and only if:
1. $T.\text{status} \in \{\text{PENDING}, \text{IN\_PROGRESS}\}$
2. $\forall D \in \text{Dependencies}(T), D.\text{status} = \text{COMPLETED}$

If any dependency is uncompleted (in `PENDING`, `IN_PROGRESS`, or `CANCELLED`), $T$ is **BLOCKED**.

---

## 2. Multi-Key Ranking Algorithm

Once candidate tasks are filtered to `READY` tasks, the scheduler applies a 5-key deterministic sorting tuple:

$$\text{SortKey}(T) = (-\text{Weight}(T.\text{priority}), \text{IsOverdueFlag}(T), \text{UrgencySeconds}(T), T.\text{created\_at}, T.\text{id})$$

### Sort Hierarchy

1. **Priority Weight (Descending)**:
   - `CRITICAL` = 4
   - `HIGH` = 3
   - `MEDIUM` = 2
   - `LOW` = 1
2. **Overdue Status (Overdue First)**:
   - Tasks whose deadline has passed are elevated above tasks with future deadlines.
3. **Deadline Urgency (Ascending Time Delta)**:
   - Tasks due sooner rank before tasks due later.
   - Tasks without a deadline receive $+\infty$ and rank after deadline tasks.
4. **Task Age (Ascending Timestamp / Oldest First)**:
   - Prevents starvation of equal-priority tasks.
5. **Task ID (Ascending)**:
   - Final unique tiebreaker ensuring 100% deterministic output.

---

## 3. Graph Algorithms Complexity

| Operation | Algorithm | Time Complexity | Space Complexity |
|---|---|---|---|
| Cycle Detection | 3-Color DFS | $O(V + E)$ | $O(V)$ |
| Topological Order | Kahn's Algorithm | $O(V + E)$ | $O(V)$ |
| Transitive Dependencies | Iterative DFS | $O(V + E)$ | $O(V)$ |
| Readiness Check | Direct In-Degree Invariant | $O(V + E)$ | $O(V)$ |
| Execution Plan | Multi-Tier Wave Simulation | $O(V \cdot (V + E))$ | $O(V)$ |
