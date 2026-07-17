"""Tests for validated, non-destructive frontend promotion."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from promote_processed_data import promote_artifact  # noqa: E402


class PromotionTests(unittest.TestCase):
    def test_promotes_registered_valid_artifact_without_removing_legacy_files(self):
        payload = {
            "metadata": {
                "generated_at": "2026-07-17T10:00:00+00:00",
                "source": "World Bank Indicators API",
                "country": "IND",
                "peers": ["CHN"],
                "start_year": 2025,
                "end_year": 2025,
                "indicator_code": "PX.REX.REER",
                "label": "Real effective exchange rate",
                "unit": "index",
                "frequency": "annual",
                "is_derived": False,
            },
            "india": [{"year": 2025, "value": 101.2}],
            "peers": {"CHN": [{"year": 2025, "value": None}]},
        }
        with tempfile.TemporaryDirectory() as processed, tempfile.TemporaryDirectory() as frontend:
            source = Path(processed) / "currency" / "real_effective_exchange_rate.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(payload), encoding="utf-8")
            legacy = Path(frontend) / "currency" / "legacy.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text('{"keep": true}', encoding="utf-8")

            destination = promote_artifact(
                "currency/real_effective_exchange_rate.json",
                processed_root=processed,
                frontend_root=frontend,
            )

            self.assertEqual(
                destination.relative_to(frontend),
                Path("currency/reer-world-bank.json"),
            )
            self.assertEqual(json.loads(destination.read_text()), payload)
            self.assertTrue(legacy.exists())


if __name__ == "__main__":
    unittest.main()
