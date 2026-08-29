import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from cli.selector import run_selector
from cli.parser import build_parser
from storage.database import Database
from zeroforge.__main__ import main


class TestSelector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "selector_test.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.parser = build_parser()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_selector_exit_option_4(self):
        with patch("builtins.input", side_effect=["4"]), patch("sys.stdout", new=StringIO()) as out:
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            self.assertIn("Goodbye!", out.getvalue())

    def test_selector_exit_keywords(self):
        for kw in ["exit", "quit", "q", "EXIT", "QUIT"]:
            with patch("builtins.input", side_effect=[kw]), patch("sys.stdout", new=StringIO()) as out:
                exit_code = run_selector(self.db, self.parser)
                self.assertEqual(exit_code, 0)
                self.assertIn("Goodbye!", out.getvalue())

    def test_selector_invalid_input_then_exit(self):
        # Provide invalid number '9', invalid string 'invalid_cmd', empty line '', then '4' to exit
        with patch("builtins.input", side_effect=["9", "invalid_cmd", "", "4"]), patch("sys.stdout", new=StringIO()) as out:
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            output = out.getvalue()
            self.assertIn("Invalid selection '9'", output)
            self.assertIn("Invalid selection 'invalid_cmd'", output)
            self.assertIn("Please enter a choice", output)
            self.assertIn("Goodbye!", output)

    def test_selector_cli_option_1(self):
        # Option 1 displays CLI guide, user presses Enter to return, then exits with 4
        with patch("builtins.input", side_effect=["1", "", "4"]), patch("sys.stdout", new=StringIO()) as out:
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            output = out.getvalue()
            self.assertIn("COMMAND LINE INTERFACE (CLI)", output)
            self.assertIn("python -m zeroforge add", output)
            self.assertIn("Goodbye!", output)

    def test_selector_repl_option_2(self):
        with patch("builtins.input", side_effect=["2", "4"]), \
             patch("cli.selector.run_repl", return_value=0) as mock_repl, \
             patch("sys.stdout", new=StringIO()):
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            mock_repl.assert_called_once_with(self.db)

    def test_selector_wizard_option_3(self):
        with patch("builtins.input", side_effect=["3", "4"]), \
             patch("cli.selector.run_wizard", return_value=0) as mock_wizard, \
             patch("sys.stdout", new=StringIO()):
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            mock_wizard.assert_called_once_with(self.db)

    def test_selector_eof_and_interrupt(self):
        with patch("builtins.input", side_effect=EOFError), patch("sys.stdout", new=StringIO()) as out:
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            self.assertIn("Goodbye!", out.getvalue())

        with patch("builtins.input", side_effect=KeyboardInterrupt), patch("sys.stdout", new=StringIO()) as out:
            exit_code = run_selector(self.db, self.parser)
            self.assertEqual(exit_code, 0)
            self.assertIn("Goodbye!", out.getvalue())

    def test_main_without_args_launches_selector(self):
        with patch("zeroforge.__main__.run_selector", return_value=0) as mock_sel:
            exit_code = main(["--db", str(self.db_path)])
            self.assertEqual(exit_code, 0)
            mock_sel.assert_called_once()

    def test_main_with_command_bypasses_selector(self):
        with patch("zeroforge.__main__.run_selector") as mock_sel, patch("sys.stdout", new=StringIO()):
            exit_code = main(["--db", str(self.db_path), "list"])
            self.assertEqual(exit_code, 0)
            mock_sel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
