import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config.capex_analysis import OUTPUTS  # noqa: E402
from promote_processed_data import artifact_routes  # noqa: E402
from validators import validate_payload  # noqa: E402


class CapexDepthArtifactTests(unittest.TestCase):
    def _load(self, key: str) -> dict:
        path = ROOT / "data" / "processed" / OUTPUTS[key]
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_payload(payload, "dated_multi_series.schema.json")
        return payload

    def test_project_quality_separates_timing_and_cost_efficiency(self):
        payload = self._load("quality")
        self.assertIn("delayed_share", payload["series"])
        self.assertIn("cost_overrun_pct", payload["series"])
        self.assertGreater(len(payload["metadata"]["sector_quality"]), 100)
        self.assertIn("2011", payload["metadata"]["break_note"])

    def test_state_panel_is_eligible_but_explicitly_non_causal(self):
        payload = self._load("states")
        estimate = payload["metadata"]["panel_estimate"]
        self.assertTrue(estimate["eligible"])
        self.assertEqual(estimate["evidence_class"], "associational")
        self.assertGreaterEqual(estimate["states"], 15)
        self.assertIn("not a causal multiplier", estimate["limitation"])

    def test_crowding_in_coefficients_obey_registered_sample_gate(self):
        payload = self._load("crowding_in")
        estimates = payload["metadata"]["lag_estimates"]
        self.assertEqual({item["lag"] for item in estimates}, {0, 1, 2, 3})
        for estimate in estimates:
            self.assertEqual(estimate["eligible"], estimate["n"] >= estimate["required_observations"])
            if not estimate["eligible"]:
                self.assertEqual(estimate["status"], "insufficient_data")

    def test_new_artifacts_use_registered_promotion_routes(self):
        routes = artifact_routes()
        for key in ("quality", "states", "crowding_in"):
            self.assertIn(Path(OUTPUTS[key]), routes)


if __name__ == "__main__":
    unittest.main()
