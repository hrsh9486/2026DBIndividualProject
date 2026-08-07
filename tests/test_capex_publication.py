"""CapEx-only catalogue and central target-boundary tests."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_capex_pipeline import TARGET_CHOICES, _select_artifact_entries  # noqa: E402
from config.capex_analysis import OUTPUTS  # noqa: E402
from sync_focused_catalogue import build_catalogue  # noqa: E402


class CapexPublicationTests(unittest.TestCase):
    def test_catalogue_discards_legacy_sections_and_assets(self):
        source = {
            "schema_version": "1.0.0",
            "public_data_root": "/data",
            "assets": {"legacy": {"schema": "annual_country_series"}},
            "sections": [{"id": "legacy"}],
        }
        catalogue = build_catalogue(source, public_data_dir=ROOT / "frontend" / "public" / "data")
        self.assertEqual([section["id"] for section in catalogue["sections"]], ["capex-transmission"])
        self.assertEqual(len(catalogue["assets"]), 12)
        self.assertTrue(all(asset["data_path"].startswith("/data/capex-analysis/") for asset in catalogue["assets"].values()))

    def test_every_registered_artifact_has_a_central_target(self):
        expected = {
            *(f"output:{key}" for key in OUTPUTS),
        }
        self.assertTrue(expected.issubset(set(TARGET_CHOICES)))

    def test_rejects_non_capex_target(self):
        with self.assertRaisesRegex(ValueError, "Unknown pipeline target"):
            _select_artifact_entries((), "output:currency")


if __name__ == "__main__":
    unittest.main()
