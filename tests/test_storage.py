import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from storage.database import Database
from core.models import Task, Priority, TaskStatus
from utils.errors import TaskNotFoundError


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
        self.db.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_get_task(self):
        now = datetime.now(timezone.utc)
        task = Task(title="Test Task", description="Desc", priority=Priority.HIGH, created_at=now)
        tid = self.db.create_task(task)
        self.assertGreater(tid, 0)

        retrieved = self.db.get_task(tid)
        self.assertEqual(retrieved.id, tid)
        self.assertEqual(retrieved.title, "Test Task")
        self.assertEqual(retrieved.description, "Desc")
        self.assertEqual(retrieved.priority, Priority.HIGH)
        self.assertEqual(retrieved.status, TaskStatus.PENDING)

    def test_get_nonexistent_task(self):
        with self.assertRaises(TaskNotFoundError):
            self.db.get_task(9999)

    def test_update_task(self):
        task = Task(title="Initial Title")
        tid = self.db.create_task(task)

        self.db.update_task(tid, title="Updated Title", priority=Priority.CRITICAL)
        retrieved = self.db.get_task(tid)
        self.assertEqual(retrieved.title, "Updated Title")
        self.assertEqual(retrieved.priority, Priority.CRITICAL)

    def test_delete_task_cascades_dependencies(self):
        t1 = self.db.create_task(Task(title="Task 1"))
        t2 = self.db.create_task(Task(title="Task 2"))

        self.db.add_dependency(t2, t1)
        self.assertEqual(self.db.get_dependencies(t2), [t1])
        self.assertEqual(self.db.get_dependents(t1), [t2])

        # Deleting t1 should cascade and remove the dependency edge
        self.db.delete_task(t1)
        self.assertFalse(self.db.task_exists(t1))
        self.assertEqual(self.db.get_dependencies(t2), [])

    def test_list_tasks_with_status_filter(self):
        t1 = self.db.create_task(Task(title="Task 1", status=TaskStatus.PENDING))
        t2 = self.db.create_task(Task(title="Task 2", status=TaskStatus.COMPLETED))

        all_tasks = self.db.list_tasks()
        self.assertEqual(len(all_tasks), 2)

        pending = self.db.list_tasks("PENDING")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, t1)

        completed = self.db.list_tasks("COMPLETED")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].id, t2)


if __name__ == "__main__":
    unittest.main()
