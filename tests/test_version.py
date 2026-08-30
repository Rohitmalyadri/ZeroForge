"""
tests/test_version.py
~~~~~~~~~~~~~~~~~~~~~
Tests for ZeroForge versioning and exposure.
"""
import unittest
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from zeroforge import __version__
from zeroforge.__main__ import main
from cli.parser import build_parser


class TestVersion(unittest.TestCase):
    def test_version_single_source_of_truth(self):
        self.assertEqual(__version__, "1.0.0")

    def test_cli_version_flag_long(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as cm, patch("sys.stdout", new=StringIO()) as out:
            parser.parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(f"ZeroForge v{__version__}", out.getvalue())

    def test_cli_version_flag_short(self):
        parser = build_parser()
        with self.assertRaises(SystemExit) as cm, patch("sys.stdout", new=StringIO()) as out:
            parser.parse_args(["-V"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(f"ZeroForge v{__version__}", out.getvalue())

    def test_cli_version_subcommand(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "version_test.db")
            with patch("sys.stdout", new=StringIO()) as out:
                exit_code = main(["--db", db_path, "version"])
                self.assertEqual(exit_code, 0)
                self.assertEqual(out.getvalue().strip(), f"ZeroForge v{__version__}")


if __name__ == "__main__":
    unittest.main()
