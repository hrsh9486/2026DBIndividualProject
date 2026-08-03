"""Pre-estimation eligibility and structured insufficiency tests."""

from datetime import date
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.alignment import AlignedRow, AlignedSample  # noqa: E402
from analysis.eligibility import evaluate_eligibility, insufficient_evidence_result  # noqa: E402
from config.evidence_specs import EVIDENCE_SPECS  # noqa: E402
from models import EvidenceStatus, ObservationStatus  # noqa: E402


def trend_sample(count, *, constant=False, future=False):
    name = "log_upi_transactions_per_capita"
    rows = []
    for index in range(count):
        year = 2018 + index // 12
        month = index % 12 + 1
        observation_date = date(year, month, 28)
        source_date = (
            date(year + 1, month, 28)
            if future and index == count - 1
            else observation_date
        )
        rows.append(AlignedRow(
            date=observation_date,
            values={name: 1.0 if constant else float(index)},
            statuses={name: ObservationStatus.ACTUAL},
            source_dates={name: source_date},
        ))
    return AlignedSample(tuple(rows), {}, {name: count})


class EvidenceEligibilityTests(unittest.TestCase):
    def test_registered_monthly_trend_passes_without_estimating(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        result = evaluate_eligibility(spec, trend_sample(36))
        self.assertTrue(result.eligible)
        self.assertTrue(all(result.checks.values()))

    def test_minimum_sample_and_variation_fail_deterministically(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        short = evaluate_eligibility(spec, trend_sample(35))
        constant = evaluate_eligibility(spec, trend_sample(36, constant=True))
        self.assertFalse(short.eligible)
        self.assertFalse(short.checks["minimum_observations"])
        self.assertFalse(constant.eligible)
        self.assertFalse(constant.checks["dependent_variation"])

    def test_future_information_is_rejected(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        result = evaluate_eligibility(spec, trend_sample(36, future=True))
        self.assertFalse(result.eligible)
        self.assertFalse(result.checks["no_future_information"])

    def test_failed_gate_becomes_publishable_insufficient_result(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        sample = trend_sample(20)
        eligibility = evaluate_eligibility(spec, sample)
        result = insufficient_evidence_result(spec, sample, eligibility)
        self.assertEqual(result.status, EvidenceStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.sample_size, 20)
        self.assertFalse(result.eligibility.eligible)
        self.assertEqual(result.estimates, ())


if __name__ == "__main__":
    unittest.main()
