import unittest
from core.models import Priority, TaskStatus
from core.validator import (
    validate_title,
    validate_priority,
    validate_status,
    validate_estimated_minutes,
    validate_due_date,
    validate_task_id,
    validate_description,
)
from utils.errors import InvalidTaskError


class TestValidator(unittest.TestCase):
    def test_validate_title(self):
        self.assertEqual(validate_title("  My Task  "), "My Task")
        with self.assertRaises(InvalidTaskError):
            validate_title("")
        with self.assertRaises(InvalidTaskError):
            validate_title("   ")
        with self.assertRaises(InvalidTaskError):
            validate_title("a" * 201)

    def test_validate_priority(self):
        self.assertEqual(validate_priority("high"), Priority.HIGH)
        self.assertEqual(validate_priority("LOW"), Priority.LOW)
        with self.assertRaises(InvalidTaskError):
            validate_priority("ultra")

    def test_validate_status(self):
        self.assertEqual(validate_status("pending"), TaskStatus.PENDING)
        self.assertEqual(validate_status("completed"), TaskStatus.COMPLETED)
        with self.assertRaises(InvalidTaskError):
            validate_status("ready")

    def test_validate_estimated_minutes(self):
        self.assertEqual(validate_estimated_minutes(30), 30)
        self.assertEqual(validate_estimated_minutes("45"), 45)
        with self.assertRaises(InvalidTaskError):
            validate_estimated_minutes(0)
        with self.assertRaises(InvalidTaskError):
            validate_estimated_minutes(-5)
        with self.assertRaises(InvalidTaskError):
            validate_estimated_minutes("abc")

    def test_validate_due_date(self):
        dt = validate_due_date("2026-12-31")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 12)
        self.assertEqual(dt.day, 31)
        self.assertEqual(dt.hour, 23)
        self.assertEqual(dt.minute, 59)

        with self.assertRaises(InvalidTaskError):
            validate_due_date("not-a-date")

    def test_validate_task_id(self):
        self.assertEqual(validate_task_id(1), 1)
        self.assertEqual(validate_task_id("5"), 5)
        with self.assertRaises(InvalidTaskError):
            validate_task_id(0)
        with self.assertRaises(InvalidTaskError):
            validate_task_id(-1)
        with self.assertRaises(InvalidTaskError):
            validate_task_id("abc")

    def test_validate_description(self):
        self.assertEqual(validate_description("  detail  "), "detail")
        self.assertEqual(validate_description(""), "")
        with self.assertRaises(InvalidTaskError):
            validate_description("a" * 2001)


if __name__ == "__main__":
    unittest.main()
