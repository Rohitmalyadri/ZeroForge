import unittest
import tempfile
from pathlib import Path
from zeroforge.__main__ import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "cli_test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *args):
        return main(["--db", self.db_path, *args])

    def test_cli_add_and_list(self):
        code = self.run_cli("add", "Task 1", "--priority", "high")
        self.assertEqual(code, 0)

        code = self.run_cli("add", "Task 2", "--priority", "critical", "--after", "1")
        self.assertEqual(code, 0)

        code = self.run_cli("list")
        self.assertEqual(code, 0)

    def test_cli_lifecycle(self):
        self.run_cli("add", "Task 1")
        code = self.run_cli("start", "1")
        self.assertEqual(code, 0)

        code = self.run_cli("done", "1")
        self.assertEqual(code, 0)

    def test_cli_ready_blocked_plan_graph(self):
        self.run_cli("add", "Design DB", "--priority", "high")
        self.run_cli("add", "Build API", "--priority", "critical", "--after", "1")

        code = self.run_cli("ready")
        self.assertEqual(code, 0)

        code = self.run_cli("blocked")
        self.assertEqual(code, 0)

        code = self.run_cli("plan")
        self.assertEqual(code, 0)

        code = self.run_cli("graph")
        self.assertEqual(code, 0)

    def test_cli_cycle_prevention(self):
        self.run_cli("add", "Task 1")
        self.run_cli("add", "Task 2", "--after", "1")

        # 1 depending on 2 would create cycle
        code = self.run_cli("dep", "add", "1", "--on", "2")
        self.assertEqual(code, 1)

    def test_cli_wizard_command_parses(self):
        # Verify wizard command exists and parses (don't actually run it
        # since it's interactive)
        from cli.parser import build_parser
        parser = build_parser()
        args = parser.parse_args(["wizard"])
        self.assertEqual(args.command, "wizard")

    def test_cli_repl_command_parses(self):
        from cli.parser import build_parser
        parser = build_parser()
        args = parser.parse_args(["repl"])
        self.assertEqual(args.command, "repl")

    def test_cli_help_includes_repl_wizard(self):
        from cli.parser import build_parser
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("repl", help_text)
        self.assertIn("wizard", help_text)


if __name__ == "__main__":
    unittest.main()
