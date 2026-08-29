import unittest
from datetime import datetime, timezone, timedelta
from core.models import Task, Priority, TaskStatus
from core.scheduler import rank_tasks, generate_plan, full_execution_order


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    def test_priority_ranking(self):
        t1 = Task(id=1, title="Low", priority=Priority.LOW, created_at=self.now)
        t2 = Task(id=2, title="Critical", priority=Priority.CRITICAL, created_at=self.now)
        t3 = Task(id=3, title="High", priority=Priority.HIGH, created_at=self.now)
        t4 = Task(id=4, title="Medium", priority=Priority.MEDIUM, created_at=self.now)

        ranked = rank_tasks([t1, t2, t3, t4], now=self.now)
        self.assertEqual([t.id for t in ranked], [2, 3, 4, 1])

    def test_overdue_and_deadline_ranking(self):
        # Overdue task should rank higher than future task of same priority
        overdue_dt = self.now - timedelta(days=1)
        future_dt = self.now + timedelta(days=2)
        far_future_dt = self.now + timedelta(days=10)

        t_overdue = Task(id=1, title="Overdue", priority=Priority.HIGH, due_at=overdue_dt, created_at=self.now)
        t_soon = Task(id=2, title="Due Soon", priority=Priority.HIGH, due_at=future_dt, created_at=self.now)
        t_later = Task(id=3, title="Due Later", priority=Priority.HIGH, due_at=far_future_dt, created_at=self.now)
        t_nodue = Task(id=4, title="No Due Date", priority=Priority.HIGH, due_at=None, created_at=self.now)

        ranked = rank_tasks([t_nodue, t_later, t_soon, t_overdue], now=self.now)
        self.assertEqual([t.id for t in ranked], [1, 2, 3, 4])

    def test_task_age_tiebreaker(self):
        # Same priority, no deadline: older task ranks first
        t_old = Task(id=1, title="Old", priority=Priority.MEDIUM, created_at=self.now - timedelta(hours=5))
        t_new = Task(id=2, title="New", priority=Priority.MEDIUM, created_at=self.now)

        ranked = rank_tasks([t_new, t_old], now=self.now)
        self.assertEqual([t.id for t in ranked], [1, 2])

    def test_generate_plan_only_returns_ready(self):
        t1 = Task(id=1, title="DB", priority=Priority.HIGH, created_at=self.now)
        t2 = Task(id=2, title="API", priority=Priority.CRITICAL, created_at=self.now) # depends on 1

        edges = [(2, 1)] # 2 depends on 1
        plan = generate_plan([t1, t2], edges, now=self.now)

        # Only Task 1 is ready, so Task 1 must be in plan, not Task 2
        self.assertEqual([t.id for t in plan], [1])

    def test_full_execution_order(self):
        t1 = Task(id=1, title="DB", priority=Priority.HIGH, created_at=self.now)
        t2 = Task(id=2, title="API", priority=Priority.CRITICAL, created_at=self.now) # depends on 1
        t3 = Task(id=3, title="Docs", priority=Priority.LOW, created_at=self.now) # independent

        edges = [(2, 1)] # 2 depends on 1
        order = full_execution_order([t1, t2, t3], edges, now=self.now)

        # Wave 1: Task 1 (High) and Task 3 (Low) are ready -> Task 1, then Task 3
        # Wave 2: Task 2 becomes ready once 1 is complete -> Task 2
        self.assertEqual([t.id for t in order], [1, 3, 2])


if __name__ == "__main__":
    unittest.main()
