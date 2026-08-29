"""
Tests for the REPL module.
"""
import unittest
import tempfile
from pathlib import Path
from storage.database import Database
from core.engine import Engine
from cli.repl import _parse_tokens, _fuzzy_match_task, COMMANDS, _COMMAND_MAP


class TestReplTokens(unittest.TestCase):
    """Test the simple tokenizer."""

    def test_parse_simple_command(self):
        tokens = _parse_tokens("list")
        self.assertEqual(tokens, ["list"])

    def test_parse_with_args(self):
        tokens = _parse_tokens("add Design Database --priority high")
        self.assertEqual(tokens, ["add", "Design", "Database", "--priority", "high"])

    def test_parse_quoted_string(self):
        tokens = _parse_tokens('add "Design the database" --priority high')
        self.assertEqual(tokens, ["add", "Design the database", "--priority", "high"])

    def test_parse_single_quoted(self):
        tokens = _parse_tokens("add 'Design the DB'")
        self.assertEqual(tokens, ["add", "Design the DB"])

    def test_parse_empty(self):
        self.assertEqual(_parse_tokens(""), [])
        self.assertEqual(_parse_tokens("   "), [])


class TestReplCommands(unittest.TestCase):
    """Test command registration."""

    def test_commands_have_unique_names(self):
        names = [c.name for c in COMMANDS]
        self.assertEqual(len(names), len(set(names)))

    def test_command_lookup_works(self):
        for cmd in COMMANDS:
            self.assertIn(cmd.name, _COMMAND_MAP)
            for alias in cmd.aliases:
                self.assertIn(alias, _COMMAND_MAP)

    def test_common_aliases_present(self):
        # Aliases that should be available
        self.assertIn("ls", _COMMAND_MAP)
        self.assertIn("rm", _COMMAND_MAP)
        self.assertIn("q", _COMMAND_MAP)
        self.assertIn("?", _COMMAND_MAP)


class TestReplFuzzyMatch(unittest.TestCase):
    """Test fuzzy task matching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "fuzzy_test.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.engine = Engine(self.db)
        # Create some test tasks
        self.engine.add_task(title="Design the database")
        self.engine.add_task(title="Build the API")
        self.engine.add_task(title="Write tests")
        self.engine.add_task(title="Deploy")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fuzzy_match_numeric(self):
        """Pure numeric input returns that ID."""
        self.assertEqual(_fuzzy_match_task(self.engine, "1"), 1)
        self.assertEqual(_fuzzy_match_task(self.engine, "3"), 3)

    def test_fuzzy_match_substring(self):
        """Substring of title returns the task ID."""
        self.assertEqual(_fuzzy_match_task(self.engine, "design"), 1)
        self.assertEqual(_fuzzy_match_task(self.engine, "API"), 2)
        self.assertEqual(_fuzzy_match_task(self.engine, "tests"), 3)

    def test_fuzzy_match_no_match(self):
        """No match returns None."""
        self.assertIsNone(_fuzzy_match_task(self.engine, "nonexistent"))
        self.assertIsNone(_fuzzy_match_task(self.engine, ""))


if __name__ == "__main__":
    unittest.main()
