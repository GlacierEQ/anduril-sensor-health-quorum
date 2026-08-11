from __future__ import annotations

import unittest

from src.sensor_health import SensorHealthQuorum


class SensorHealthEvolutionTests(unittest.TestCase):
    def test_correlated_reporters_count_as_one_domain(self):
        q = SensorHealthQuorum(suspend_below=0.3, reinstate_above=0.7)
        q.report("cam-a", "fusion", 0.1, fault_domain="rack-a")
        receipt = q.report("cam-b", "fusion", 0.9, fault_domain="rack-a")
        self.assertEqual(receipt.independent_domains, 1)
        self.assertEqual(receipt.domain_weights[0].reporters, ("cam-a", "cam-b"))
        self.assertAlmostEqual(receipt.domain_weights[0].effective_weight, 1.0)

    def test_correlated_multiplicity_cannot_reinstate(self):
        q = SensorHealthQuorum(
            suspend_below=0.4,
            reinstate_above=0.55,
            required_recovery_rounds=2,
            min_recovery_domains=2,
        )
        q.report("bad", "sensor-x", 0.0, fault_domain="rack-a")
        for reporter in ("good-1", "good-2", "good-3"):
            receipt = q.report(
                reporter,
                "sensor-x",
                1.0,
                fault_domain="rack-a",
                round_id="round-1",
            )
        self.assertGreaterEqual(receipt.smoothed_score, q.reinstate_above)
        self.assertEqual(receipt.independent_domains, 1)
        self.assertEqual(receipt.reason, "INSUFFICIENT_INDEPENDENT_DOMAINS")
        self.assertFalse(q.can_vote("sensor-x"))

    def test_recovery_requires_threshold_then_distinct_rounds(self):
        q = SensorHealthQuorum(
            suspend_below=0.4,
            reinstate_above=0.6,
            required_recovery_rounds=2,
            min_recovery_domains=2,
        )
        q.report("a", "sensor-x", 0.0, fault_domain="rack-a")
        q.report("b", "sensor-x", 0.0, fault_domain="rack-b")
        q.report("a", "sensor-x", 1.0, fault_domain="rack-a")
        below = q.report("b", "sensor-x", 1.0, fault_domain="rack-b")
        self.assertEqual(below.reason, "RECOVERY_THRESHOLD_NOT_MET")
        no_round = q.report("a", "sensor-x", 1.0, fault_domain="rack-a")
        self.assertGreaterEqual(no_round.smoothed_score, q.reinstate_above)
        self.assertEqual(no_round.reason, "ROUND_ID_REQUIRED_FOR_RECOVERY")
        first = q.report("a", "sensor-x", 1.0, fault_domain="rack-a", round_id="r1")
        duplicate = q.report("b", "sensor-x", 1.0, fault_domain="rack-b", round_id="r1")
        second = q.report("a", "sensor-x", 1.0, fault_domain="rack-a", round_id="r2")
        self.assertEqual(first.recovery_streak, 1)
        self.assertEqual(duplicate.recovery_streak, 1)
        self.assertEqual(second.transition, "REINSTATE")
        self.assertTrue(q.can_vote("sensor-x"))

    def test_receipt_and_invalid_labels(self):
        q = SensorHealthQuorum()
        receipt = q.report("a", "sensor-x", 0.1, fault_domain="rack-a")
        self.assertEqual(q.last_receipt("sensor-x"), receipt)
        self.assertEqual(len(receipt.fingerprint()), 64)
        with self.assertRaises(ValueError):
            q.report("reporter", "subject", 0.5, fault_domain="")
        with self.assertRaises(ValueError):
            q.report("reporter", "subject", 0.5, round_id="")


if __name__ == "__main__":
    unittest.main()
