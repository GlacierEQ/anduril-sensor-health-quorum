from __future__ import annotations
import unittest
from src.sensor_health import SensorHealthQuorum

class HealthTests(unittest.TestCase):
    def test_suspend(self):
        q = SensorHealthQuorum(suspend_below=0.4)
        q.report("s1", "s2", 0.1)
        q.report("s3", "s2", 0.1)
        self.assertFalse(q.can_vote("s2"))

    def test_self_report_forbidden(self):
        q = SensorHealthQuorum()
        with self.assertRaises(ValueError):
            q.report("s1", "s1", 1.0)

if __name__ == "__main__":
    unittest.main()
