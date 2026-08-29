import unittest
from core.dependency import DependencyGraph


class TestDependency(unittest.TestCase):
    def test_empty_graph(self):
        graph = DependencyGraph([])
        self.assertFalse(graph.has_cycle())
        self.assertIsNone(graph.find_cycle())
        self.assertEqual(graph.topological_order(), [])

    def test_linear_dependency(self):
        # 2 depends on 1, 3 depends on 2
        edges = [(2, 1), (3, 2)]
        graph = DependencyGraph(edges)

        self.assertFalse(graph.has_cycle())
        self.assertEqual(graph.topological_order(), [1, 2, 3])
        self.assertEqual(graph.direct_deps(2), {1})
        self.assertEqual(graph.direct_deps(1), set())
        self.assertEqual(graph.direct_dependents(1), {2})
        self.assertEqual(graph.direct_dependents(2), {3})

    def test_diamond_dependency(self):
        # 2 depends on 1, 3 depends on 1, 4 depends on 2 and 3
        edges = [(2, 1), (3, 1), (4, 2), (4, 3)]
        graph = DependencyGraph(edges)

        self.assertFalse(graph.has_cycle())
        topo = graph.topological_order()
        self.assertEqual(topo[0], 1)
        self.assertEqual(topo[-1], 4)
        self.assertEqual(set(topo[1:3]), {2, 3})

    def test_direct_cycle(self):
        # 1 depends on 2, 2 depends on 1
        edges = [(1, 2), (2, 1)]
        graph = DependencyGraph(edges)

        self.assertTrue(graph.has_cycle())
        cycle = graph.find_cycle()
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])  # starts and ends on same node

    def test_indirect_cycle(self):
        # 1 depends on 3, 2 depends on 1, 3 depends on 2
        edges = [(2, 1), (3, 2), (1, 3)]
        graph = DependencyGraph(edges)

        self.assertTrue(graph.has_cycle())
        cycle = graph.find_cycle()
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])

    def test_would_create_cycle(self):
        edges = [(2, 1), (3, 2)]
        graph = DependencyGraph(edges)

        # 1 depends on 3 would create cycle: 1 -> 3 -> 2 -> 1
        cycle = graph.would_create_cycle(1, 3)
        self.assertIsNotNone(cycle)

        # 4 depends on 3 is fine
        self.assertIsNone(graph.would_create_cycle(4, 3))

    def test_ancestors(self):
        edges = [(2, 1), (3, 2), (4, 3), (5, 6)]
        graph = DependencyGraph(edges)

        self.assertEqual(graph.ancestors(4), {1, 2, 3})
        self.assertEqual(graph.ancestors(1), set())
        self.assertEqual(graph.ancestors(5), {6})

    def test_compute_status_ready_and_blocked(self):
        # 2 depends on 1, 3 depends on 2
        edges = [(2, 1), (3, 2)]
        graph = DependencyGraph(edges)

        # Initially, no tasks completed
        status = graph.compute_status(task_ids={1, 2, 3}, completed_ids=set())
        self.assertEqual(status[1], "READY")
        self.assertEqual(status[2], "BLOCKED")
        self.assertEqual(status[3], "BLOCKED")

        # After task 1 is completed
        status2 = graph.compute_status(task_ids={2, 3}, completed_ids={1})
        self.assertEqual(status2[2], "READY")
        self.assertEqual(status2[3], "BLOCKED")

        # After task 2 is also completed
        status3 = graph.compute_status(task_ids={3}, completed_ids={1, 2})
        self.assertEqual(status3[3], "READY")

    def test_blocking_tasks(self):
        edges = [(3, 1), (3, 2)]
        graph = DependencyGraph(edges)

        self.assertEqual(graph.blocking_tasks(3, completed_ids=set()), [1, 2])
        self.assertEqual(graph.blocking_tasks(3, completed_ids={1}), [2])
        self.assertEqual(graph.blocking_tasks(3, completed_ids={1, 2}), [])


if __name__ == "__main__":
    unittest.main()
