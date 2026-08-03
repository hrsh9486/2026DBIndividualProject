"""CapEx-only catalogue and promotion boundary tests."""

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from promote_processed_data import promote_artifact  # noqa: E402
from sync_focused_catalogue import build_catalogue  # noqa: E402


def dated_payload() -> dict:
    return {
        "metadata": {
            "generated_at": "2026-08-03T10:00:00+00:00",
            "source": [{"name": "Test source"}],
            "frequency": "annual",
            "start_date": "2024-03-31",
            "end_date": "2024-03-31",
            "indicator_code": "CAPEX_TEST",
            "label": "CapEx test",
            "default_unit": "percent",
            "series_order": ["value"],
            "is_derived": True,
        },
        "series": {
            "value": {
                "label": "Value",
                "entity": "IND",
                "unit": "percent",
                "values": [{"date": "2024-03-31", "value": 1.0}],
            }
        },
    }


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

    def test_promotes_registered_capex_artifact(self):
        payload = dated_payload()
        relative = Path("capex-analysis/investment-quality.json")
        with tempfile.TemporaryDirectory() as processed, tempfile.TemporaryDirectory() as frontend:
            source = Path(processed) / relative
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(payload), encoding="utf-8")
            destination = promote_artifact(relative, processed_root=processed, frontend_root=frontend)
            self.assertEqual(destination.relative_to(frontend), relative)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), payload)

    def test_rejects_non_capex_artifact(self):
        with self.assertRaisesRegex(ValueError, "No active CapEx output contract"):
            promote_artifact("currency/reer-world-bank.json")


if __name__ == "__main__":
    unittest.main()
