"""Cross-field quality rules that JSON Schema cannot express."""

from __future__ import annotations

import math
import re
from typing import Any

from config.evidence_specs import SPECIFICATION_REGISTRY_VERSION, evidence_specs_for_lens
from config.focused_indicators import get_focused_bundle
from config.indicators import Contract
from validators.schema import validate_payload


class EvidenceValidationError(ValueError):
    """Raised when an evidence report is structurally valid but incoherent."""


_INFERENTIAL_STATUSES = {
    "supported",
    "not_supported",
    "mixed",
    "failed_diagnostics",
}
_PROHIBITED_CAUSAL_PATTERNS = (
    r"\bcauses?\b",
    r"\bcaused\b",
    r"\bcausal effect\b",
    r"\bleads? to\b",
    r"\bresults? in\b",
    r"\bdrives?\b",
)


def _finite_numbers(value: Any, path: str = "<root>") -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise EvidenceValidationError(f"Evidence contains a non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_numbers(item, f"{path}/{index}")
    elif isinstance(value, dict):
        for key, item in value.items():
            _finite_numbers(item, f"{path}/{key}")


def validate_evidence_report(payload: dict, *, enforce_registry: bool = True) -> None:
    """Validate schema, registered scope, intervals, statuses and interpretation."""
    validate_payload(payload, Contract.EVIDENCE_REPORT.value)
    _finite_numbers(payload)
    metadata = payload["metadata"]
    analyses = payload["analyses"]
    analysis_keys = [item["analysis_key"] for item in analyses]
    if len(analysis_keys) != len(set(analysis_keys)):
        raise EvidenceValidationError("Evidence analysis keys must be unique")
    if metadata["analysis_order"] != analysis_keys:
        raise EvidenceValidationError("Evidence analyses do not match metadata.analysis_order")
    if metadata["specification_registry_version"] != SPECIFICATION_REGISTRY_VERSION:
        raise EvidenceValidationError("Evidence registry version does not match the running registry")

    specs = ()
    if enforce_registry:
        specs = evidence_specs_for_lens(metadata["lens_key"])
        expected = [spec.key for spec in specs]
        if not expected or analysis_keys != expected:
            raise EvidenceValidationError(
                f"Evidence analyses must exactly match the registered order for {metadata['lens_key']}"
            )
        for analysis, spec in zip(analyses, specs):
            if analysis["specification_version"] != spec.version:
                raise EvidenceValidationError(
                    f"Specification version drift for {analysis['analysis_key']}"
                )
            if analysis["causal"] != spec.causal:
                raise EvidenceValidationError(f"Causal flag drift for {analysis['analysis_key']}")
            registered_identity = {
                "label": spec.label,
                "claim": spec.claim,
                "null_hypothesis": spec.null_hypothesis,
                "evidence_class": spec.evidence_class.value,
                "focal_terms": list(spec.focal_terms),
                "expected_direction": spec.expected_direction.value,
                "support_rule": spec.support_rule.value,
            }
            for field, expected_value in registered_identity.items():
                if analysis[field] != expected_value:
                    raise EvidenceValidationError(
                        f"Registered {field} drift for {analysis['analysis_key']}"
                    )
            dependent_frequency = next(
                item.expected_frequency for item in spec.inputs if item.role == "dependent"
            )
            registered_method = {
                "estimator": spec.estimator.value,
                "formula": spec.formula,
                "covariance": spec.covariance.value,
                "max_lags": spec.covariance_max_lags,
                "alignment": spec.alignment.value,
            }
            if analysis["sample"]["frequency"] != dependent_frequency:
                raise EvidenceValidationError(
                    f"Registered frequency drift for {analysis['analysis_key']}"
                )
            if analysis["method"] != registered_method:
                raise EvidenceValidationError(
                    f"Registered method drift for {analysis['analysis_key']}"
                )
            if spec.limitation not in analysis["limitation"]:
                raise EvidenceValidationError(
                    f"Registered limitation is missing for {analysis['analysis_key']}"
                )

        bundle = get_focused_bundle(metadata["lens_key"])
        if metadata["label"] != f"{bundle.label} — evidence":
            raise EvidenceValidationError("Evidence report label drifted from the lens registry")
        if metadata["research_question"] != bundle.research_question:
            raise EvidenceValidationError("Evidence research question drifted from the lens registry")
        expected_source_paths = {
            item.asset_path
            for spec in specs
            for item in spec.inputs
        }
        actual_source_paths = [item["path"] for item in metadata["source_assets"]]
        if len(actual_source_paths) != len(set(actual_source_paths)):
            raise EvidenceValidationError("Evidence source assets must be unique")
        if set(actual_source_paths) != expected_source_paths:
            raise EvidenceValidationError("Evidence source assets do not match registered inputs")
        if any(item["contract"] != "dated_multi_series" for item in metadata["source_assets"]):
            raise EvidenceValidationError("Registered evidence inputs require dated_multi_series assets")
        families = {spec.multiple_testing_family for spec in specs}
        alphas = {spec.alpha for spec in specs}
        expected_multiple_testing = {
            "method": "benjamini_hochberg",
            "family": next(iter(families)),
            "alpha": next(iter(alphas)),
        }
        if metadata["multiple_testing"] != expected_multiple_testing:
            raise EvidenceValidationError("Multiple-testing policy drifted from the registry")

    source_starts = [item["start_date"] for item in metadata["source_assets"]]
    source_ends = [item["end_date"] for item in metadata["source_assets"]]
    common_start = max(source_starts)
    common_end = min(source_ends)
    if common_start > common_end:
        raise EvidenceValidationError("Evidence source artifacts have no overlapping coverage")

    multiple_testing = metadata["multiple_testing"]
    for analysis in analyses:
        key = analysis["analysis_key"]
        sample = analysis["sample"]
        if (sample["start_date"] is None) != (sample["end_date"] is None):
            raise EvidenceValidationError(f"Sample dates must both be set or null: {key}")
        if sample["start_date"] is not None:
            if sample["start_date"] > sample["end_date"]:
                raise EvidenceValidationError(f"Sample ends before it starts: {key}")
            if sample["start_date"] < common_start or sample["end_date"] > common_end:
                raise EvidenceValidationError(f"Sample lies outside source coverage: {key}")

        estimates = analysis["estimates"]
        def validate_estimate(estimate: dict, *, require_adjusted: bool) -> None:
            interval = estimate["confidence_interval"]
            if interval is not None:
                if interval[0] > interval[1]:
                    raise EvidenceValidationError(f"Confidence interval is reversed: {key}/{estimate['term']}")
                if not interval[0] <= estimate["value"] <= interval[1]:
                    raise EvidenceValidationError(f"Estimate lies outside its interval: {key}/{estimate['term']}")
                if estimate["confidence_level"] is None:
                    raise EvidenceValidationError(f"Confidence interval lacks a confidence level: {key}/{estimate['term']}")
            elif estimate["confidence_level"] is not None:
                raise EvidenceValidationError(f"Confidence level lacks an interval: {key}/{estimate['term']}")
            if (
                require_adjusted
                and multiple_testing["method"] != "none"
                and estimate["is_focal"]
                and estimate["p_value"] is not None
                and estimate["adjusted_p_value"] is None
            ):
                raise EvidenceValidationError(f"Adjusted p-value is required: {key}/{estimate['term']}")

        for estimate in estimates:
            validate_estimate(estimate, require_adjusted=True)

        status = analysis["status"]
        focal = [item for item in estimates if item["is_focal"]]
        if status in _INFERENTIAL_STATUSES:
            current_spec = (
                next(item for item in specs if item.key == key)
                if enforce_registry
                else None
            )
            eligibility = analysis["eligibility"]
            if eligibility is None or not eligibility["eligible"]:
                raise EvidenceValidationError(
                    f"Inferential evidence requires a passed eligibility result: {key}"
                )
            if not focal:
                raise EvidenceValidationError(f"Inferential evidence lacks a focal estimate: {key}")
            if (
                current_spec is not None
                and [item["term"] for item in focal] != list(current_spec.focal_terms)
            ):
                raise EvidenceValidationError(
                    f"Focal estimates do not match the registered order: {key}"
                )
            for estimate in focal:
                if (
                    estimate["standard_error"] is None
                    or estimate["confidence_interval"] is None
                    or estimate["p_value"] is None
                    or estimate["adjusted_p_value"] is None
                ):
                    raise EvidenceValidationError(f"Focal inferential estimate is incomplete: {key}")
            if current_spec is not None:
                diagnostic_keys = [item["key"] for item in analysis["diagnostics"]]
                if diagnostic_keys != list(current_spec.diagnostics):
                    raise EvidenceValidationError(
                        f"Diagnostics do not match the registered order: {key}"
                    )
                robustness_keys = [
                    item["specification"] for item in analysis["robustness"]
                ]
                if robustness_keys != list(current_spec.robustness):
                    raise EvidenceValidationError(
                        f"Robustness checks do not match the registered order: {key}"
                    )
                alpha = metadata["multiple_testing"]["alpha"]
                expected_direction = current_spec.expected_direction.value
                main_support = all(
                    item["adjusted_p_value"] < alpha
                    and (
                        expected_direction == "two_sided"
                        or (expected_direction == "positive" and item["value"] > 0)
                        or (expected_direction == "negative" and item["value"] < 0)
                    )
                    for item in focal
                )
                failed_diagnostics = any(
                    item["passed"] is False for item in analysis["diagnostics"]
                )
                if status == "supported" and (not main_support or failed_diagnostics):
                    raise EvidenceValidationError(
                        f"Supported status contradicts the registered decision rule: {key}"
                    )
                if status == "not_supported" and (main_support or failed_diagnostics):
                    raise EvidenceValidationError(
                        f"Not-supported status contradicts the registered decision rule: {key}"
                    )
                if status == "failed_diagnostics" and not failed_diagnostics:
                    raise EvidenceValidationError(
                        f"Failed-diagnostics status has no failed diagnostic: {key}"
                    )
        elif status == "descriptive_only":
            if any(
                item["p_value"] is not None or item["adjusted_p_value"] is not None
                for item in estimates
            ):
                raise EvidenceValidationError(f"Descriptive evidence cannot contain p-values: {key}")
            if analysis["grade"] != "descriptive":
                raise EvidenceValidationError(f"Descriptive evidence must have descriptive grade: {key}")
        elif status == "insufficient_data":
            eligibility = analysis["eligibility"]
            if estimates:
                raise EvidenceValidationError(f"Insufficient evidence cannot contain estimates: {key}")
            if eligibility is None or eligibility["eligible"]:
                raise EvidenceValidationError(f"Insufficient evidence requires a failed eligibility result: {key}")
            if sample["n"] != eligibility["available_observations"]:
                raise EvidenceValidationError(f"Eligibility count does not match sample size: {key}")

        eligibility = analysis["eligibility"]
        if (
            eligibility is not None
            and sample["n"] != eligibility["available_observations"]
        ):
            raise EvidenceValidationError(f"Eligibility count does not match sample size: {key}")

        for robustness in analysis["robustness"]:
            focal_estimate = robustness["focal_estimate"]
            if focal_estimate is not None:
                validate_estimate(focal_estimate, require_adjusted=False)
            if (
                robustness["status"] in _INFERENTIAL_STATUSES
                and focal_estimate is None
            ):
                raise EvidenceValidationError(
                    f"Inferential robustness check lacks a focal estimate: "
                    f"{key}/{robustness['specification']}"
                )

        if not analysis["causal"]:
            interpretation = analysis["practical_interpretation"].lower()
            if any(re.search(pattern, interpretation) for pattern in _PROHIBITED_CAUSAL_PATTERNS):
                raise EvidenceValidationError(f"Non-causal evidence uses prohibited causal language: {key}")
