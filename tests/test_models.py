import unittest
from datetime import datetime, timezone
from core.models import Task, Priority, TaskStatus, ComputedStatus, DependencyEdge


class TestModels(unittest.TestCase):
    def test_priority_enum(self):
        self.assertEqual(Priority.LOW.weight, 1)
        self.assertEqual(Priority.MEDIUM.weight, 2)
        self.assertEqual(Priority.HIGH.weight, 3)
        self.assertEqual(Priority.CRITICAL.weight, 4)

        self.assertEqual(Priority.from_str("high"), Priority.HIGH)
        self.assertEqual(Priority.from_str("CRITICAL"), Priority.CRITICAL)
        with self.assertRaises(ValueError):
            Priority.from_str("invalid")

    def test_task_status_enum(self):
        self.assertEqual(TaskStatus.from_str("pending"), TaskStatus.PENDING)
        self.assertEqual(TaskStatus.from_str("in_progress"), TaskStatus.IN_PROGRESS)
        self.assertEqual(TaskStatus.from_str("completed"), TaskStatus.COMPLETED)
        self.assertEqual(TaskStatus.from_str("cancelled"), TaskStatus.CANCELLED)
        with self.assertRaises(ValueError):
            TaskStatus.from_str("ready")  # ready is derived, not persistent

    def test_task_defaults(self):
        task = Task(title="Test Task")
        self.assertIsNone(task.id)
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.description, "")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.priority, Priority.MEDIUM)
        self.assertIsNone(task.due_at)
        self.assertIsNone(task.estimated_minutes)
        self.assertTrue(task.is_active)
        self.assertFalse(task.is_done)
        self.assertFalse(task.is_in_progress)

    def test_task_properties(self):
        task = Task(title="Done Task", status=TaskStatus.COMPLETED)
        self.assertTrue(task.is_done)
        self.assertFalse(task.is_active)

        task2 = Task(title="In Progress", status=TaskStatus.IN_PROGRESS)
        self.assertTrue(task2.is_in_progress)
        self.assertTrue(task2.is_active)

    def test_dependency_edge_self_reference_rejection(self):
        with self.assertRaises(ValueError):
            DependencyEdge(task_id=1, depends_on_id=1)

        edge = DependencyEdge(task_id=2, depends_on_id=1)
        self.assertEqual(edge.task_id, 2)
        self.assertEqual(edge.depends_on_id, 1)


if __name__ == "__main__":
    unittest.main()
