import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8"))
POSITION = json.loads((ROOT / "machine" / "canonical-position.json").read_text(encoding="utf-8"))


class ExcellenceStateContractTests(unittest.TestCase):
    def test_state_is_canonical_and_evolving(self):
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(STATE["gates"]["CANONICAL_POSITION_RESOLVED"]["status"], "PASS")
        self.assertEqual(STATE["gates"]["EVOLUTION_CURSOR_DEFINED"]["status"], "PASS")
        self.assertEqual(STATE["canonical_position_ref"], "machine/canonical-position.json")

    def test_position_preserves_identity_and_lineage(self):
        self.assertEqual(POSITION["repository"], STATE["repository"])
        self.assertEqual(POSITION["position_state"], "RESOLVED")
        policy = POSITION["integration_policy"]
        self.assertTrue(policy["preserve_repository_identity"])
        self.assertTrue(policy["preserve_lineage"])
        self.assertTrue(policy["presentation_independent"])
        self.assertTrue(policy["absorption_requires_functional_equivalence"])
        self.assertTrue(policy["absorption_requires_proof_equivalence"])

    def test_evolution_cursor_is_material(self):
        self.assertTrue(STATE["evolution_cursor"].startswith("next:"))
        self.assertNotIn("canonical_position_only_if_estate_role_resolved", STATE["evolution_cursor"])
        self.assertTrue(POSITION["next_evolution"])


if __name__ == "__main__":
    unittest.main()
