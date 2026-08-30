"""
tests/test_edge_cases.py
~~~~~~~~~~~~~~~~~~~~~~~~
Comprehensive edge-case and boundary testing for ZeroForge.
"""
import os
import unittest
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from core.engine import Engine
from core.models import Task, TaskStatus, Priority
from core.validator import (
    validate_title,
    validate_description,
    validate_priority,
    validate_status,
    validate_estimated_minutes,
    validate_due_date,
    MAX_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
)
from core.dependency import DependencyGraph
from core.scheduler import rank_tasks, generate_plan
from storage.database import Database
from utils.dates import now_utc, is_overdue, parse_date
from utils.errors import (
    ZeroForgeError,
    InvalidTaskError,
    TaskNotFoundError,
    DependencyError,
    DependencyCycleError,
)
from cli.repl import _parse_tokens, _fuzzy_match_task
from cli.wizard import _parse_natural_date
from zeroforge.__main__ import main, get_default_db_path


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "edge_cases.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.engine = Engine(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    # ------------------------------------------------------------------ #
    # 1. Empty Task Database Operations
    # ------------------------------------------------------------------ #

    def test_empty_db_queries(self):
        self.assertEqual(self.engine.list_tasks(), [])
        self.assertEqual(self.engine.ready_tasks(), [])
        self.assertEqual(self.engine.blocked_tasks(), [])
        self.assertEqual(self.engine.generate_plan(), [])
        graph_data = self.engine.get_graph_data()
        self.assertEqual(graph_data["tasks"], {})
        self.assertEqual(graph_data["edges"], [])
        self.assertEqual(graph_data["topo_order"], [])

    def test_empty_db_cli_commands(self):
        with patch("sys.stdout", new=StringIO()):
            self.assertEqual(main(["--db", str(self.db_path), "list"]), 0)
            self.assertEqual(main(["--db", str(self.db_path), "ready"]), 0)
            self.assertEqual(main(["--db", str(self.db_path), "blocked"]), 0)
            self.assertEqual(main(["--db", str(self.db_path), "plan"]), 0)
            self.assertEqual(main(["--db", str(self.db_path), "graph"]), 0)

    # ------------------------------------------------------------------ #
    # 2. Validation Bounds & Characters
    # ------------------------------------------------------------------ #

    def test_title_boundaries(self):
        # Empty title
        with self.assertRaises(InvalidTaskError):
            validate_title("")
        with self.assertRaises(InvalidTaskError):
            validate_title("   ")

        # Max length title
        max_title = "A" * MAX_TITLE_LENGTH
        self.assertEqual(validate_title(max_title), max_title)

        # Exceeds max length
        with self.assertRaises(InvalidTaskError):
            validate_title("A" * (MAX_TITLE_LENGTH + 1))

    def test_description_boundaries(self):
        # Empty description is valid
        self.assertEqual(validate_description(""), "")

        # Max length description
        max_desc = "D" * MAX_DESCRIPTION_LENGTH
        self.assertEqual(validate_description(max_desc), max_desc)

        # Exceeds max description length
        with self.assertRaises(InvalidTaskError):
            validate_description("D" * (MAX_DESCRIPTION_LENGTH + 1))

    def test_unicode_and_special_characters(self):
        unicode_title = "🚀 Deploy Microservice — (v1.0.0) & [Production-Ready] / 特殊文字"
        task = self.engine.add_task(title=unicode_title, description="Contains € and üñîçødë chars")
        self.assertEqual(task.title, unicode_title)
        retrieved = self.engine.get_task(task.id)
        self.assertEqual(retrieved.title, unicode_title)
        self.assertEqual(retrieved.description, "Contains € and üñîçødë chars")

    # ------------------------------------------------------------------ #
    # 3. Graph Dependency Complex Topologies
    # ------------------------------------------------------------------ #

    def test_self_dependency_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        with self.assertRaises(DependencyError):
            self.engine.add_dependency(t1.id, t1.id)

    def test_2_node_cycle_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        t2 = self.engine.add_task(title="Task 2", after=[t1.id])
        with self.assertRaises(DependencyCycleError):
            self.engine.add_dependency(t1.id, t2.id)

    def test_3_node_cycle_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        t2 = self.engine.add_task(title="Task 2", after=[t1.id])
        t3 = self.engine.add_task(title="Task 3", after=[t2.id])
        with self.assertRaises(DependencyCycleError):
            self.engine.add_dependency(t1.id, t3.id)

    def test_diamond_graph_resolution(self):
        # 1 -> 2 -> 4
        # 1 -> 3 -> 4
        t1 = self.engine.add_task(title="Root 1")
        t2 = self.engine.add_task(title="Branch 2", after=[t1.id])
        t3 = self.engine.add_task(title="Branch 3", after=[t1.id])
        t4 = self.engine.add_task(title="Leaf 4", after=[t2.id, t3.id])

        # Initially, only t1 is READY
        ready_ids = [t.id for t in self.engine.ready_tasks()]
        self.assertEqual(ready_ids, [t1.id])

        # Complete t1 -> t2 and t3 become ready; t4 remains blocked
        self.engine.complete_task(t1.id)
        ready_ids = [t.id for t in self.engine.ready_tasks()]
        self.assertEqual(set(ready_ids), {t2.id, t3.id})
        self.assertEqual(self.engine.get_computed_status(t4.id), "BLOCKED")

        # Complete t2 -> t4 is still blocked by t3
        self.engine.complete_task(t2.id)
        ready_ids = [t.id for t in self.engine.ready_tasks()]
        self.assertEqual(ready_ids, [t3.id])
        self.assertEqual(self.engine.get_computed_status(t4.id), "BLOCKED")

        # Complete t3 -> t4 is finally READY
        self.engine.complete_task(t3.id)
        ready_ids = [t.id for t in self.engine.ready_tasks()]
        self.assertEqual(ready_ids, [t4.id])
        self.assertEqual(self.engine.get_computed_status(t4.id), "READY")

    def test_cascade_delete_dependency_edges(self):
        t1 = self.engine.add_task(title="Task 1")
        t2 = self.engine.add_task(title="Task 2", after=[t1.id])
        self.assertEqual(self.db.all_edges(), [(t2.id, t1.id)])

        # Delete t1 -> edge should be cascade deleted
        self.engine.delete_task(t1.id)
        self.assertEqual(self.db.all_edges(), [])
        # t2 should now be READY since its blocking dependency was deleted
        self.assertEqual(self.engine.get_computed_status(t2.id), "READY")

    # ------------------------------------------------------------------ #
    # 4. State Transitions & Lifecycle Rules
    # ------------------------------------------------------------------ #

    def test_start_blocked_task_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        t2 = self.engine.add_task(title="Task 2", after=[t1.id])
        with self.assertRaises(InvalidTaskError):
            self.engine.start_task(t2.id)

    def test_start_already_completed_task_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        self.engine.complete_task(t1.id)
        with self.assertRaises(InvalidTaskError):
            self.engine.start_task(t1.id)

    def test_cancel_completed_task_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        self.engine.complete_task(t1.id)
        with self.assertRaises(InvalidTaskError):
            self.engine.cancel_task(t1.id)

    def test_double_complete_rejected(self):
        t1 = self.engine.add_task(title="Task 1")
        self.engine.complete_task(t1.id)
        with self.assertRaises(InvalidTaskError):
            self.engine.complete_task(t1.id)

    # ------------------------------------------------------------------ #
    # 5. Scheduler Urgency & Overdue Behavior
    # ------------------------------------------------------------------ #

    def test_overdue_sorting_urgency(self):
        now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
        past_due = now - timedelta(days=2)
        future_due = now + timedelta(days=2)

        t_future = Task(title="Future Due", id=1, priority=Priority.HIGH, due_at=future_due)
        t_overdue = Task(title="Overdue Task", id=2, priority=Priority.HIGH, due_at=past_due)
        t_no_due = Task(title="No Due Date", id=3, priority=Priority.HIGH, due_at=None)

        ranked = rank_tasks([t_future, t_no_due, t_overdue], now=now)
        # Overdue should rank first, then future deadline, then no deadline
        self.assertEqual([t.id for t in ranked], [2, 1, 3])

    # ------------------------------------------------------------------ #
    # 6. REPL & Wizard Edge Parsing
    # ------------------------------------------------------------------ #

    def test_repl_tokenizer_edge_cases(self):
        # Empty string
        self.assertEqual(_parse_tokens(""), [])
        # Escaped / nested quotes
        tokens = _parse_tokens('add "Task with \'inner single\'" --priority high')
        self.assertEqual(tokens, ["add", "Task with 'inner single'", "--priority", "high"])
        tokens2 = _parse_tokens("add 'Task with \"inner double\"' -p critical")
        self.assertEqual(tokens2, ["add", 'Task with "inner double"', "-p", "critical"])

    def test_wizard_date_parsing_edge_cases(self):
        # Invalid inputs
        self.assertIsNone(_parse_natural_date("random text"))
        self.assertIsNone(_parse_natural_date(""))
        self.assertIsNone(_parse_natural_date("32-13-2026"))

        # Valid days
        dt_today = _parse_natural_date("today")
        self.assertIsNotNone(dt_today)
        dt_tomorrow = _parse_natural_date("tomorrow")
        self.assertIsNotNone(dt_tomorrow)
        dt_in_3_days = _parse_natural_date("in 3 days")
        self.assertIsNotNone(dt_in_3_days)

    # ------------------------------------------------------------------ #
    # 7. Environment Override
    # ------------------------------------------------------------------ #

    def test_env_db_override(self):
        custom_path = "/custom/path/tasks.db"
        with patch.dict(os.environ, {"ZEROFORGE_DB": custom_path}):
            resolved = get_default_db_path()
            self.assertEqual(str(resolved), str(Path(custom_path)))


if __name__ == "__main__":
    unittest.main()
