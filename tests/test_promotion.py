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

    def test_promotes_focused_dated_bundle_to_matching_public_path(self):
        payload = {
            "metadata": {
                "generated_at": "2026-07-21T10:00:00+00:00",
                "source": [{"name": "NPCI"}],
                "frequency": "mixed",
                "start_date": "2024-01-31",
                "end_date": "2024-01-31",
                "indicator_code": "DIGITAL_INTEGRATION_UPI_TAX",
                "label": "Digital integration and tax capacity",
                "default_unit": "mixed",
                "series_order": ["upi_transactions_per_capita"],
                "is_derived": True,
            },
            "series": {
                "upi_transactions_per_capita": {
                    "label": "UPI transactions per capita",
                    "entity": "IND",
                    "unit": "transactions_per_person",
                    "values": [{"date": "2024-01-31", "value": 0.1}],
                }
            },
        }
        with tempfile.TemporaryDirectory() as processed, tempfile.TemporaryDirectory() as frontend:
            source = Path(processed) / "digital-integration" / "upi-and-tax-capacity.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(payload), encoding="utf-8")

            destination = promote_artifact(
                "digital-integration/upi-and-tax-capacity.json",
                processed_root=processed,
                frontend_root=frontend,
            )

            self.assertEqual(
                destination.relative_to(frontend),
                Path("digital-integration/upi-and-tax-capacity.json"),
            )
            self.assertEqual(json.loads(destination.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
