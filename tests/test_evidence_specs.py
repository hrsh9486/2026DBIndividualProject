"""Registration tests for the frozen initial evidence designs."""

from datetime import date
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config.evidence_specs import (  # noqa: E402
    EVIDENCE_SPECS,
    ExpectedDirection,
    SPECIFICATION_REGISTRY_VERSION,
    validate_evidence_specs,
)


class EvidenceSpecificationTests(unittest.TestCase):
    def test_registry_is_internally_consistent(self):
        validate_evidence_specs()
        self.assertEqual(SPECIFICATION_REGISTRY_VERSION, "1.2.0")
        self.assertEqual(
            set(EVIDENCE_SPECS),
            {
                "debt-interest-burden-change",
                "primary-balance-debt-change",
                "upi-adoption-trend",
            },
        )

    def test_upi_start_break_and_uncertainty_are_frozen(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        self.assertEqual(spec.analysis_start_date, date(2017, 4, 30))
        self.assertEqual(spec.break_date, date(2020, 4, 30))
        self.assertEqual(spec.covariance.value, "HAC")
        self.assertEqual(spec.covariance_max_lags, 12)
        self.assertEqual(spec.focal_terms, ("annualised_underlying_trend",))
        self.assertEqual(spec.expected_direction, ExpectedDirection.POSITIVE)
        self.assertFalse(spec.causal)

    def test_fiscal_models_share_one_testing_family(self):
        fiscal = [
            spec
            for spec in EVIDENCE_SPECS.values()
            if spec.lens_key == "fiscal_capacity"
        ]
        self.assertEqual(len(fiscal), 2)
        self.assertEqual(
            {spec.multiple_testing_family for spec in fiscal},
            {"fiscal_capacity_primary"},
        )
        self.assertTrue(all(spec.minimum_observations == 30 for spec in fiscal))
        self.assertEqual(
            {spec.key: spec.expected_direction for spec in fiscal},
            {
                "debt-interest-burden-change": ExpectedDirection.POSITIVE,
                "primary-balance-debt-change": ExpectedDirection.NEGATIVE,
            },
        )


if __name__ == "__main__":
    unittest.main()
