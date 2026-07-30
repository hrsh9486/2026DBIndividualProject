"""Evidence schema, cross-field validation and atomic publication tests."""

from copy import deepcopy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_fixtures import (  # noqa: E402
    descriptive_result,
    digital_report,
    insufficient_result,
    supported_result,
)
from exporters import publish_evidence_report  # noqa: E402
from validators import EvidenceValidationError, validate_evidence_report  # noqa: E402


class EvidenceContractTests(unittest.TestCase):
    def test_supported_descriptive_and_insufficient_reports_are_valid(self):
        for result in (supported_result(), descriptive_result(), insufficient_result()):
            with self.subTest(status=result.status.value):
                validate_evidence_report(digital_report(result))

    def test_confidence_interval_must_contain_estimate(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["estimates"][0]["confidence_interval"] = [0.11, 0.14]
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_adjusted_p_value_is_required_for_registered_family(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["estimates"][0]["adjusted_p_value"] = None
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_descriptive_result_cannot_smuggle_in_a_p_value(self):
        payload = digital_report(descriptive_result())
        payload["analyses"][0]["estimates"][0]["p_value"] = 0.04
        payload["analyses"][0]["estimates"][0]["adjusted_p_value"] = 0.04
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_noncausal_interpretation_rejects_causal_language(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["practical_interpretation"] = (
            "The synthetic trend causes higher adoption."
        )
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_registered_method_cannot_drift_under_the_same_version(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["method"]["formula"] = "outcome ~ result_selected_control"
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_inferential_result_requires_all_registered_robustness_checks(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["robustness"].pop()
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_inferential_result_requires_passed_pre_estimation_gate(self):
        payload = digital_report(supported_result())
        payload["analyses"][0]["eligibility"]["eligible"] = False
        with self.assertRaises(EvidenceValidationError):
            validate_evidence_report(payload)

    def test_supported_status_must_follow_registered_direction_and_threshold(self):
        wrong_direction = digital_report(supported_result())
        wrong_direction["analyses"][0]["estimates"][0]["value"] = -0.1
        wrong_direction["analyses"][0]["estimates"][0]["confidence_interval"] = [
            -0.14,
            -0.06,
        ]
        high_adjusted_p = digital_report(supported_result())
        high_adjusted_p["analyses"][0]["estimates"][0]["adjusted_p_value"] = 0.2
        for payload in (wrong_direction, high_adjusted_p):
            with self.subTest(payload=payload["analyses"][0]["estimates"][0]):
                with self.assertRaises(EvidenceValidationError):
                    validate_evidence_report(payload)

    def test_invalid_candidate_does_not_replace_existing_evidence(self):
        payload = digital_report(supported_result())
        invalid = deepcopy(payload)
        invalid["analyses"][0]["estimates"][0]["confidence_interval"] = [0.2, 0.3]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence.json"
            publish_evidence_report(payload, destination)
            original = json.loads(destination.read_text(encoding="utf-8"))
            with self.assertRaises(EvidenceValidationError):
                publish_evidence_report(invalid, destination)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), original)

    def test_public_evidence_schema_matches_authoritative_copy(self):
        self.assertEqual(
            (ROOT / "schemas/evidence_report.schema.json").read_bytes(),
            (
                ROOT
                / "frontend/public/data/schemas/evidence_report.schema.json"
            ).read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
