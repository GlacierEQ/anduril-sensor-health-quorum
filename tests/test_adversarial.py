from __future__ import annotations
import unittest
from src.sensor_health import SensorHealthQuorum

class Adv(unittest.TestCase):
    def test_self_report_refused(self):
        q = SensorHealthQuorum(suspend_below=0.4)
        with self.assertRaises(ValueError):
            q.report("s1", "s1", 1.0)
    def test_health_out_of_range(self):
        q = SensorHealthQuorum()
        with self.assertRaises(ValueError):
            q.report("s1", "s2", 1.5)
    def test_suspend_then_cannot_vote(self):
        q = SensorHealthQuorum(suspend_below=0.4)
        q.report("a", "b", 0.0)
        q.report("c", "b", 0.0)
        self.assertFalse(q.can_vote("b"))

