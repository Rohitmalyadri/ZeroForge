"""
tests/test_health.py
~~~~~~~~~~~~~~~~~~~~
Tests for the application health check.
"""
import unittest
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from core.health import run_health_check, check_environment, check_core_components, check_interfaces
from core.engine import Engine
from storage.database import Database
from zeroforge.__main__ import main


class TestHealthCheck(unittest.TestCase):
    def test_check_environment(self):
        results = check_environment()
        self.assertTrue(len(results) >= 2)
        for name, ok, detail in results:
            self.assertTrue(ok, f"Environment check failed for {name}: {detail}")

    def test_check_core_components(self):
        results = check_core_components()
        self.assertTrue(len(results) >= 4)
        for name, ok, detail in results:
            self.assertTrue(ok, f"Core check failed for {name}: {detail}")

    def test_check_interfaces(self):
        results = check_interfaces()
        self.assertTrue(len(results) >= 3)
        for name, ok, detail in results:
            self.assertTrue(ok, f"Interface check failed for {name}: {detail}")

    def test_run_health_check_healthy(self):
        all_passed, report = run_health_check()
        self.assertTrue(all_passed)
        self.assertIn("Overall Status: HEALTHY", report)
        self.assertIn("ZEROFORGE HEALTH CHECK", report)
        self.assertIn("Environment", report)
        self.assertIn("Core Components", report)
        self.assertIn("User Interfaces", report)

    def test_health_check_safety_does_not_mutate_user_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            user_db_path = Path(temp_dir) / "production_user.db"
            db = Database(user_db_path)
            db.initialize()
            engine = Engine(db)
            task = engine.add_task(title="Important User Task", priority="HIGH")

            # Run health check
            all_passed, report = run_health_check()
            self.assertTrue(all_passed)

            # Verify original database is untouched
            tasks = engine.list_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].id, task.id)
            self.assertEqual(tasks[0].title, "Important User Task")

    def test_cli_health_subcommand(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "cli_health_test.db")
            with patch("sys.stdout", new=StringIO()) as out:
                exit_code = main(["--db", db_path, "health"])
                self.assertEqual(exit_code, 0)
                output = out.getvalue()
                self.assertIn("Overall Status: HEALTHY", output)


if __name__ == "__main__":
    unittest.main()
