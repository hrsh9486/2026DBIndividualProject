"""Registered-path loading and end-to-end preparation tests."""

import calendar
from datetime import date
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis import RegisteredArtifactLoader, prepare_registered_analysis  # noqa: E402
from config.evidence_specs import EVIDENCE_SPECS  # noqa: E402


def digital_payload(month_count=40):
    values = []
    for index in range(month_count):
        year = 2018 + index // 12
        month = index % 12 + 1
        values.append({
            "date": date(
                year,
                month,
                calendar.monthrange(year, month)[1],
            ).isoformat(),
            "value": float(index + 1),
            "status": "actual",
        })
    return {
        "metadata": {
            "generated_at": "2026-07-28T10:00:00+00:00",
            "source": [{"name": "Synthetic test source"}],
            "frequency": "mixed",
            "start_date": values[0]["date"],
            "end_date": values[-1]["date"],
            "indicator_code": "SYNTHETIC_DIGITAL",
            "label": "Synthetic digital fixture",
            "default_unit": "mixed",
            "series_order": ["upi_transactions_per_capita"],
            "is_derived": True,
        },
        "series": {
            "upi_transactions_per_capita": {
                "label": "UPI transactions per capita",
                "entity": "IND",
                "unit": "transactions_per_person",
                "values": values,
            }
        },
    }


class EvidenceLoaderTests(unittest.TestCase):
    def test_registered_loader_validates_and_types_observations(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "digital-integration/upi-and-tax-capacity.json"
            )
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(digital_payload()), encoding="utf-8")
            loaded = RegisteredArtifactLoader(processed_root=directory).load(
                spec.inputs[0]
            )
            self.assertEqual(len(loaded.observations), 40)
            self.assertEqual(loaded.observations[0].date, date(2018, 1, 31))
            self.assertEqual(loaded.unit, "transactions_per_person")
            self.assertEqual(
                loaded.artifact_sha256,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_pipeline_prepares_eligible_sample_without_estimation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "digital-integration/upi-and-tax-capacity.json"
            )
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(digital_payload()), encoding="utf-8")
            prepared = prepare_registered_analysis(
                "upi-adoption-trend",
                loader=RegisteredArtifactLoader(processed_root=directory),
            )
            self.assertTrue(prepared.eligibility.eligible)
            self.assertEqual(len(prepared.sample.rows), 40)
            self.assertEqual(len(prepared.source_assets), 1)

    def test_entity_drift_is_rejected(self):
        payload = digital_payload()
        payload["series"]["upi_transactions_per_capita"]["entity"] = "USA"
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        with tempfile.TemporaryDirectory() as directory:
            path = (
                Path(directory)
                / "digital-integration/upi-and-tax-capacity.json"
            )
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                RegisteredArtifactLoader(processed_root=directory).load(
                    spec.inputs[0]
                )


if __name__ == "__main__":
    unittest.main()
