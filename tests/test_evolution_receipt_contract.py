from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text())
POSITION = json.loads((ROOT / "machine" / "canonical-position.json").read_text())
CONTRACT = json.loads((ROOT / "machine" / "target-contract.json").read_text())
RECEIPT = json.loads(
    (ROOT / "machine" / "evolution-receipts" / "2026-08-11-correlated-health-hysteresis.json").read_text()
)


class EvolutionReceiptContractTests(unittest.TestCase):
    def test_exact_candidate_consumed_current_cursor(self):
        self.assertEqual(
            RECEIPT["consumed_cursor"],
            "next:correlated_fault_detection_recovery_hysteresis_and_explainable_weighting",
        )
        self.assertEqual(RECEIPT["candidate_source_sha"], "eaf59fa675a2f0e21a58242cd5a78ab3ea656a19")
        self.assertEqual(RECEIPT["workflow_run"], 31453906929)
        self.assertEqual(RECEIPT["proof"], {"python": "PASS", "go": "PASS"})

    def test_next_cursor_is_consistent_everywhere(self):
        expected = "next:authenticated_fault_domain_attestation_evidence_freshness_and_durable_decision_receipt_chain"
        self.assertEqual(STATE["evolution_cursor"], expected)
        self.assertEqual(POSITION["next_evolution_cursor"], expected)
        self.assertEqual(CONTRACT["target"]["next_cursor"], expected)
        self.assertEqual(RECEIPT["next_cursor"], expected)

    def test_provenance_limits_remain_explicit(self):
        text = " ".join(POSITION["nonclaims"] + CONTRACT["nonclaims"] + RECEIPT["truth_boundaries"]).lower()
        self.assertIn("caller-supplied", text)
        self.assertIn("not externally authenticated", text)
        self.assertIn("freshness", text)
        self.assertIn("durab", text)

    def test_target_contract_is_valid_and_conflict_free(self):
        raw = (ROOT / "machine" / "target-contract.json").read_text()
        self.assertNotIn("<<<<<<<", raw)
        self.assertNotIn("=======", raw)
        self.assertNotIn(">>>>>>>", raw)
        self.assertEqual(CONTRACT["identity"]["repository_id"], STATE["repository"])


if __name__ == "__main__":
    unittest.main()
