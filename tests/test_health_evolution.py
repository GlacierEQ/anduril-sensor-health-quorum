from __future__ import annotations

import unittest

from src.sensor_health import SensorHealthQuorum


class SensorHealthEvolutionTests(unittest.TestCase):
    def test_correlated_reporters_share_one_domain_weight(self):
        q = SensorHealthQuorum(suspend_below=0.3, reinstate_above=0.7)
        q.report("cam-a", "fusion-1", 0.1, fault_domain="rack-a")
        receipt = q.report("cam-b", "fusion-1", 0.9, fault_domain="rack-a")
        self.assertEqual(receipt.independent_domains, 1)
        self.assertEqual(len(receipt.domain_weights), 1)
        domain = receipt.domain_weights[0]
        self.assertEqual(domain.fault_domain, "rack-a")
        self.assertEqual(domain.reporters, ("cam-a", "cam-b"))
        self.assertAlmostEqual(domain.domain_health, 0.5)
        self.assertAlmostEqual(domain.effective_weight, 1.0)

    def test_independent_domains_receive_equal_explainable_weight(self):
        q = SensorHealthQuorum(suspend_below=0.2, reinstate_above=0.8)
        q.report("a1", "sensor-x", 0.2, fault_domain="rack-a")
        q.report("a2", "sensor-x", 0.4, fault_domain="rack-a")
        receipt = q.report("b1", "sensor-x", 0.9, fault_domain="rack-b")
        self.assertEqual(receipt.independent_domains, 2)
        self.assertEqual(
            [(row.fault_domain, row.reporters) for row in receipt.domain_weights],
            [("rack-a", ("a1", "a2")), ("rack-b", ("b1",))],
        )
        self.assertTrue(all(abs(row.effective_weight - 0.5) < 1e-12 for row in receipt.domain_weights))
        self.assertAlmostEqual(receipt.observed_health, (0.3 + 0.9) / 2)

    def test_correlated_multiplicity_cannot_fake_independent_recovery(self):
        q = SensorHealthQuorum(
            suspend_below=0.4,
            reinstate_above=0.65,
            required_recovery_rounds=2,
            min_recovery_domains=2,
        )
        q.report("bad-a", "sensor-x", 0.0, fault_domain="rack-a")
        q.report("bad-b", "sensor-x", 0.0, fault_domain="rack-b")
        self.assertFalse(q.can_vote("sensor-x"))

        # Many favorable reporters from one correlated domain still count once.
        for reporter in ("good-1", "good-2", "good-3"):
            receipt = q.report(
                reporter,
                "sensor-x",
                1.0,
                fault_domain="rack-c",
                round_id="round-1",
            )
        self.assertGreaterEqual(receipt.smoothed_score, q.reinstate_above)
        self.assertEqual(receipt.reason, "INSUFFICIENT_INDEPENDENT_DOMAINS" if receipt.independent_domains < 2 else receipt.reason)
        self.assertFalse(q.can_vote("sensor-x"))

    def test_recovery_requires_distinct_rounds_and_independent_domains(self):
        q = SensorHealthQuorum(
            suspend_below=0.4,
            reinstate_above=0.6,
            required_recovery_rounds=2,
            min_recovery_domains=2,
        )
        q.report("a", "sensor-x", 0.0, fault_domain="rack-a")
        q.report("b", "sensor-x", 0.0, fault_domain="rack-b")
        self.assertFalse(q.can_vote("sensor-x"))

        # Raise both domain scores; recovery only counts when a distinct round_id is supplied.
        q.report("a", "sensor-x", 1.0, fault_domain="rack-a")
        no_round = q.report("b", "sensor-x", 1.0, fault_domain="rack-b")
        self.assertEqual(no_round.reason, "ROUND_ID_REQUIRED_FOR_RECOVERY")
        self.assertFalse(q.can_vote("sensor-x"))

        first = q.report("a", "sensor-x", 1.0, fault_domain="rack-a", round_id="r1")
        self.assertEqual(first.recovery_streak, 1)
        self.assertFalse(q.can_vote("sensor-x"))
        duplicate = q.report("b", "sensor-x", 1.0, fault_domain="rack-b", round_id="r1")
        self.assertEqual(duplicate.recovery_streak, 1)
        self.assertFalse(q.can_vote("sensor-x"))
        second = q.report("a", "sensor-x", 1.0, fault_domain="rack-a", round_id="r2")
        self.assertEqual(second.transition, "REINSTATE")
        self.assertEqual(second.reason, "RECOVERY_HYSTERESIS_SATISFIED")
        self.assertTrue(q.can_vote("sensor-x"))

    def test_recovery_receipt_is_explainable(self):
        q = SensorHealthQuorum(suspend_below=0.4, reinstate_above=0.7)
        q.report("a", "sensor-x", 0.0, fault_domain="rack-a")
        receipt = q.report("b", "sensor-x", 1.0, fault_domain="rack-b", round_id="r1")
        self.assertEqual(receipt.subject, "sensor-x")
        self.assertEqual(len(receipt.fingerprint()), 64)
        self.assertEqual(q.last_receipt("sensor-x"), receipt)
        self.assertIn(receipt.reason, {
            "RECOVERY_THRESHOLD_NOT_MET",
            "RECOVERY_HYSTERESIS_INCOMPLETE",
        })

    def test_invalid_thresholds_and_empty_evidence_labels_fail_closed(self):
        with self.assertRaises(ValueError):
            SensorHealthQuorum(suspend_below=0.8, reinstate_above=0.7)
        q = SensorHealthQuorum()
        with self.assertRaises(ValueError):
            q.report("", "subject", 0.5)
        with self.assertRaises(ValueError):
            q.report("reporter", "subject", 0.5, fault_domain="")
        with self.assertRaises(ValueError):
            q.report("reporter", "subject", 0.5, round_id="")


if __name__ == "__main__":
    unittest.main()
