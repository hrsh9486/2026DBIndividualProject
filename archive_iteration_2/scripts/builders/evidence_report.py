"""Build versioned evidence reports from registered specifications and results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from config.evidence_specs import (
    EVIDENCE_SPECS,
    SPECIFICATION_REGISTRY_VERSION,
    evidence_specs_for_lens,
)
from config.focused_indicators import get_focused_bundle
from models import (
    DiagnosticResult,
    EligibilityResult,
    Estimate,
    EvidenceResult,
    RobustnessResult,
    SourceAsset,
)


def _estimate_payload(estimate: Estimate) -> dict:
    interval = None
    if (
        estimate.confidence_interval_low is not None
        and estimate.confidence_interval_high is not None
    ):
        interval = [
            estimate.confidence_interval_low,
            estimate.confidence_interval_high,
        ]
    return {
        "term": estimate.term,
        "value": estimate.value,
        "unit": estimate.unit,
        "is_focal": estimate.is_focal,
        "standard_error": estimate.standard_error,
        "confidence_level": estimate.confidence_level,
        "confidence_interval": interval,
        "p_value": estimate.p_value,
        "adjusted_p_value": estimate.adjusted_p_value,
    }


def _diagnostic_payload(diagnostic: DiagnosticResult) -> dict:
    return {
        "key": diagnostic.key,
        "value": diagnostic.value,
        "threshold": diagnostic.threshold,
        "passed": diagnostic.passed,
        "interpretation": diagnostic.interpretation,
    }


def _robustness_payload(result: RobustnessResult) -> dict:
    return {
        "specification": result.specification,
        "status": result.status.value,
        "focal_estimate": (
            _estimate_payload(result.focal_estimate)
            if result.focal_estimate is not None
            else None
        ),
        "sample_size": result.sample_size,
        "note": result.note,
    }


def _eligibility_payload(result: EligibilityResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "eligible": result.eligible,
        "required_observations": result.required_observations,
        "available_observations": result.available_observations,
        "reason": result.reason,
        "checks": dict(result.checks),
    }


def _analysis_payload(result: EvidenceResult) -> dict:
    spec = EVIDENCE_SPECS[result.analysis_key]
    frequency = next(item.expected_frequency for item in spec.inputs if item.role == "dependent")
    limitations = [spec.limitation]
    if result.limitation and result.limitation != spec.limitation:
        limitations.append(result.limitation)
    return {
        "analysis_key": spec.key,
        "specification_version": spec.version,
        "label": spec.label,
        "claim": spec.claim,
        "null_hypothesis": spec.null_hypothesis,
        "evidence_class": spec.evidence_class.value,
        "causal": spec.causal,
        "focal_terms": list(spec.focal_terms),
        "expected_direction": spec.expected_direction.value,
        "support_rule": spec.support_rule.value,
        "status": result.status.value,
        "grade": result.grade.value,
        "sample": {
            "n": result.sample_size,
            "start_date": result.start_date.isoformat() if result.start_date else None,
            "end_date": result.end_date.isoformat() if result.end_date else None,
            "frequency": frequency,
            "excluded": dict(result.exclusion_summary),
        },
        "method": {
            "estimator": spec.estimator.value,
            "formula": spec.formula,
            "covariance": spec.covariance.value if spec.covariance else None,
            "max_lags": spec.covariance_max_lags,
            "alignment": spec.alignment.value,
        },
        "estimates": [_estimate_payload(item) for item in result.estimates],
        "diagnostics": [_diagnostic_payload(item) for item in result.diagnostics],
        "robustness": [_robustness_payload(item) for item in result.robustness],
        "eligibility": _eligibility_payload(result.eligibility),
        "practical_interpretation": result.practical_interpretation,
        "limitation": " ".join(limitations),
    }


def build_evidence_report(
    lens_key: str,
    results: Sequence[EvidenceResult],
    *,
    source_assets: Sequence[SourceAsset],
    code_version: str,
    software_versions: Mapping[str, str],
) -> dict:
    """Assemble, but do not estimate, one lens-level evidence publication."""
    bundle = get_focused_bundle(lens_key)
    specs = evidence_specs_for_lens(lens_key)
    if not specs:
        raise ValueError(f"No evidence specifications are registered for {lens_key}")
    expected_order = [spec.key for spec in specs]
    result_by_key = {result.analysis_key: result for result in results}
    if len(result_by_key) != len(results):
        raise ValueError("Evidence results contain duplicate analysis keys")
    if set(result_by_key) != set(expected_order):
        raise ValueError(
            f"Evidence results for {lens_key} must exactly match registered analyses: "
            f"{', '.join(expected_order)}"
        )
    if not source_assets:
        raise ValueError("Evidence reports require at least one source artifact")
    if not code_version:
        raise ValueError("Evidence reports require a code version")
    if not software_versions:
        raise ValueError("Evidence reports require software versions")
    families = {spec.multiple_testing_family for spec in specs}
    alphas = {spec.alpha for spec in specs}
    if len(families) != 1 or len(alphas) != 1:
        raise ValueError("A lens-level report currently requires one testing family and alpha")

    ordered_results = [result_by_key[key] for key in expected_order]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lens_key": lens_key,
            "label": f"{bundle.label} — evidence",
            "research_question": bundle.research_question,
            "specification_registry_version": SPECIFICATION_REGISTRY_VERSION,
            "code_version": code_version,
            "source_assets": [
                {
                    "path": asset.path,
                    "contract": asset.contract,
                    "sha256": asset.sha256,
                    "generated_at": asset.generated_at,
                    "start_date": asset.start_date.isoformat(),
                    "end_date": asset.end_date.isoformat(),
                }
                for asset in source_assets
            ],
            "analysis_order": expected_order,
            "multiple_testing": {
                "method": "benjamini_hochberg",
                "family": next(iter(families)),
                "alpha": next(iter(alphas)),
            },
            "software_versions": dict(sorted(software_versions.items())),
        },
        "analyses": [_analysis_payload(result) for result in ordered_results],
    }
