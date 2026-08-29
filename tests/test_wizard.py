"""
Tests for the wizard module.
"""
import unittest
from datetime import datetime, timezone
from cli.wizard import _parse_natural_date


class TestNaturalDateParsing(unittest.TestCase):
    """Test natural-language date parsing."""

    def setUp(self):
        # Use a fixed reference time
        from unittest.mock import patch
        from cli import wizard
        self._ref_time = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
        # Mock now_utc in wizard module
        self._patcher = patch.object(wizard, "now_utc", return_value=self._ref_time)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_parse_today(self):
        result = _parse_natural_date("today")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 8)
        self.assertEqual(result.day, 29)

    def test_parse_tomorrow(self):
        result = _parse_natural_date("tomorrow")
        self.assertIsNotNone(result)
        self.assertEqual(result.day, 30)

    def test_parse_in_n_days(self):
        result = _parse_natural_date("in 7 days")
        self.assertIsNotNone(result)
        self.assertEqual(result.day, 5)  # 29 + 7 = 5 Sep

    def test_parse_iso_date(self):
        result = _parse_natural_date("2026-12-31")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 31)

    def test_parse_invalid(self):
        result = _parse_natural_date("not a date")
        self.assertIsNone(result)

    def test_parse_empty(self):
        result = _parse_natural_date("")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
