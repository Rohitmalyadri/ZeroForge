"""
core/dependency.py
~~~~~~~~~~~~~~~~~~
Pure graph algorithms for ZeroForge's dependency engine.

This module has NO database or CLI knowledge.  It operates on plain integers
(task IDs) and edge lists.  This makes it trivially testable.

Algorithms implemented (all from scratch — no NetworkX):

1. Cycle detection — DFS with WHITE/GRAY/BLACK node coloring.
   - WHITE: not yet visited
   - GRAY:  currently on the DFS stack (being explored)
   - BLACK: fully explored
   A back-edge from GRAY→GRAY indicates a cycle.
   Complexity: O(V + E)

2. Topological sort — Kahn's algorithm (BFS-based).
   Produces a deterministic order by sorting the ready queue at each step.
   Complexity: O(V + E)

3. Ready/Blocked classification — direct dependency check.
   A task is READY if all its direct dependencies are in the completed set.
   Complexity: O(V + E) for the full set.

4. Ancestor traversal — DFS to find all transitive dependencies.
   Complexity: O(V + E) per query.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# DependencyGraph
# ---------------------------------------------------------------------------

class DependencyGraph:
    """
    Represents a directed graph of task dependencies.

    Edge direction: depends_on_id → task_id
    (i.e., task_id depends on depends_on_id)

    Parameters
    ----------
    edges : list of (task_id, depends_on_id) tuples
            Meaning: task_id depends on depends_on_id.
    """

    def __init__(self, edges: List[Tuple[int, int]]) -> None:
        # adjacency: node → set of nodes it depends on
        self._deps: Dict[int, Set[int]] = {}
        # reverse: node → set of nodes that depend on it
        self._rdeps: Dict[int, Set[int]] = {}

        for (task_id, dep_id) in edges:
            self._deps.setdefault(task_id, set()).add(dep_id)
            self._rdeps.setdefault(dep_id, set()).add(task_id)
            # Ensure all nodes appear in both dicts.
            self._deps.setdefault(dep_id, set())
            self._rdeps.setdefault(task_id, set())

    # ------------------------------------------------------------------ #
    # Node helpers                                                         #
    # ------------------------------------------------------------------ #

    def nodes(self) -> Set[int]:
        """Return all node IDs known to the graph."""
        return set(self._deps.keys()) | set(self._rdeps.keys())

    def direct_deps(self, node: int) -> Set[int]:
        """Return the set of tasks that *node* directly depends on."""
        return set(self._deps.get(node, set()))

    def direct_dependents(self, node: int) -> Set[int]:
        """Return the set of tasks that directly depend on *node*."""
        return set(self._rdeps.get(node, set()))

    # ------------------------------------------------------------------ #
    # Cycle detection — DFS WHITE/GRAY/BLACK                              #
    # ------------------------------------------------------------------ #

    def has_cycle(self) -> bool:
        """Return True if the graph contains any cycle."""
        return self.find_cycle() is not None

    def find_cycle(self) -> Optional[List[int]]:
        """
        Find and return a cycle if one exists, or None.

        Returns the cycle as a list of node IDs, e.g. [A, B, C, A].
        The first and last element are the same to make the cycle explicit.

        Uses iterative DFS with a parent-path stack to reconstruct the cycle.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[int, int] = {}
        parent: Dict[int, Optional[int]] = {}

        all_nodes = sorted(self.nodes())  # sorted for determinism

        for start in all_nodes:
            if color.get(start, WHITE) != WHITE:
                continue

            # Iterative DFS using an explicit stack.
            # Stack entries: (node, iterator_over_predecessors)
            # We traverse BACKWARDS through _rdeps to follow the edge direction
            # correctly for dependency graphs.
            # Actually we want to detect: A depends on B depends on A
            # Edges in _deps: A→{B}, B→{A}
            # DFS on _deps: from A, visit B; from B, A is GRAY → cycle.

            stack: List[Tuple[int, iter]] = []
            color[start] = GRAY
            parent[start] = None
            stack.append((start, iter(sorted(self._deps.get(start, set())))))

            while stack:
                node, children = stack[-1]
                try:
                    child = next(children)
                    child_color = color.get(child, WHITE)
                    if child_color == GRAY:
                        # Found a back edge → cycle.
                        return self._reconstruct_cycle(parent, node, child)
                    elif child_color == WHITE:
                        color[child] = GRAY
                        parent[child] = node
                        stack.append((child, iter(sorted(self._deps.get(child, set())))))
                except StopIteration:
                    color[node] = BLACK
                    stack.pop()

        return None

    def _reconstruct_cycle(
        self,
        parent: Dict[int, Optional[int]],
        from_node: int,
        cycle_start: int,
    ) -> List[int]:
        """
        Reconstruct the cycle path from the parent map.

        *from_node* has an edge to *cycle_start* which is GRAY (already on stack).
        We walk the parent chain from *from_node* back to *cycle_start*.
        """
        path = [cycle_start]
        current = from_node
        while current != cycle_start:
            path.append(current)
            p = parent.get(current)
            if p is None:
                break
            current = p
        path.append(cycle_start)
        path.reverse()
        return path

    def would_create_cycle(self, new_task_id: int, new_dep_id: int) -> Optional[List[int]]:
        """
        Check whether adding edge (new_task_id → new_dep_id) would create a cycle.

        Returns the cycle path if it would, None otherwise.

        This is more efficient than adding the edge and then checking because
        it avoids mutating the graph.
        """
        # Adding task_id → dep_id creates a cycle iff dep_id already has
        # new_task_id as a transitive dependency (i.e., new_task_id is an
        # ancestor of new_dep_id).
        if new_task_id == new_dep_id:
            return [new_task_id, new_dep_id]

        # Build a temporary graph with the new edge and detect cycles.
        all_edges: List[Tuple[int, int]] = []
        for node, deps in self._deps.items():
            for dep in deps:
                all_edges.append((node, dep))
        all_edges.append((new_task_id, new_dep_id))

        temp = DependencyGraph(all_edges)
        return temp.find_cycle()

    # ------------------------------------------------------------------ #
    # Topological sort — Kahn's algorithm                                 #
    # ------------------------------------------------------------------ #

    def topological_order(self, include_ids: Optional[Set[int]] = None) -> List[int]:
        """
        Return nodes in topological order using Kahn's algorithm.

        Nodes with no dependencies come first.  Among nodes with equal
        in-degree the queue is sorted by ID for determinism.

        If *include_ids* is provided, only those nodes are included in
        the sort (useful for sub-graphs).

        Raises RuntimeError if the graph contains a cycle (caller should
        check with has_cycle first).
        """
        if include_ids is None:
            include_ids = self.nodes()

        # Build in-degree count restricted to include_ids.
        in_degree: Dict[int, int] = {n: 0 for n in include_ids}
        for node in include_ids:
            for dep in self._deps.get(node, set()):
                if dep in include_ids:
                    in_degree[node] = in_degree.get(node, 0) + 1

        # Kahn's BFS — use a sorted deque for determinism.
        queue: deque[int] = deque(sorted(n for n, d in in_degree.items() if d == 0))
        result: List[int] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            # Reduce in-degree of dependents.
            for dependent in sorted(self._rdeps.get(node, set())):
                if dependent not in include_ids:
                    continue
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    # Insert in sorted position for determinism.
                    insert_sorted(queue, dependent)

        if len(result) != len(include_ids):
            raise RuntimeError(
                "Cycle detected during topological sort.  "
                "Call has_cycle() before topological_order()."
            )

        return result

    # ------------------------------------------------------------------ #
    # Ancestor traversal                                                   #
    # ------------------------------------------------------------------ #

    def ancestors(self, node: int) -> Set[int]:
        """
        Return all transitive dependencies of *node* (everything it depends
        on, directly or indirectly).

        Uses iterative DFS.
        """
        visited: Set[int] = set()
        stack = list(sorted(self._deps.get(node, set())))

        while stack:
            dep = stack.pop()
            if dep in visited:
                continue
            visited.add(dep)
            stack.extend(sorted(self._deps.get(dep, set())))

        return visited

    # ------------------------------------------------------------------ #
    # Ready / Blocked classification                                       #
    # ------------------------------------------------------------------ #

    def compute_status(
        self,
        task_ids: Set[int],
        completed_ids: Set[int],
    ) -> Dict[int, str]:
        """
        Classify each task in *task_ids* as 'READY' or 'BLOCKED'.

        A task is READY when all its direct dependencies are in *completed_ids*.
        A task is BLOCKED otherwise.

        Parameters
        ----------
        task_ids      : set of task IDs to classify (should exclude completed/cancelled)
        completed_ids : set of task IDs whose status is COMPLETED

        Returns a dict mapping task_id → 'READY' | 'BLOCKED'.
        """
        result: Dict[int, str] = {}
        for tid in task_ids:
            deps = self._deps.get(tid, set())
            if all(d in completed_ids for d in deps):
                result[tid] = "READY"
            else:
                result[tid] = "BLOCKED"
        return result

    def blocking_tasks(self, task_id: int, completed_ids: Set[int]) -> List[int]:
        """
        Return the list of direct dependency IDs that are blocking *task_id*.

        A dependency blocks task_id if it is NOT in completed_ids.
        """
        deps = self._deps.get(task_id, set())
        return sorted(d for d in deps if d not in completed_ids)


# ---------------------------------------------------------------------------
# Helper: insert into a sorted deque
# ---------------------------------------------------------------------------

def insert_sorted(q: deque, value: int) -> None:
    """Insert *value* into deque *q* maintaining sorted order (ascending)."""
    # Convert, insert, re-sort (small queues in practice).
    items = list(q)
    items.append(value)
    items.sort()
    q.clear()
    q.extend(items)
