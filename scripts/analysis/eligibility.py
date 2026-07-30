"""Deterministic sample-eligibility gates for registered evidence analyses."""

from __future__ import annotations

from config.evidence_specs import EVIDENCE_SPECS, EvidenceSpec
from models import (
    EligibilityResult,
    EvidenceGrade,
    EvidenceResult,
    EvidenceStatus,
)

from .alignment import AlignedSample


def _has_variation(values: list[float]) -> bool:
    return len({round(value, 12) for value in values}) > 1


def _matrix_rank(columns: list[list[float]], *, tolerance: float = 1e-10) -> int:
    if not columns:
        return 0
    matrix = [list(row) for row in zip(*columns)]
    rows = len(matrix)
    cols = len(matrix[0])
    rank = 0
    for column in range(cols):
        pivot = next(
            (
                row
                for row in range(rank, rows)
                if abs(matrix[row][column]) > tolerance
            ),
            None,
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        pivot_value = matrix[rank][column]
        matrix[rank] = [value / pivot_value for value in matrix[rank]]
        for row in range(rows):
            if row == rank:
                continue
            factor = matrix[row][column]
            if abs(factor) > tolerance:
                matrix[row] = [
                    current - factor * pivot_item
                    for current, pivot_item in zip(matrix[row], matrix[rank])
                ]
        rank += 1
        if rank == rows:
            break
    return rank


def evaluate_eligibility(spec: EvidenceSpec, sample: AlignedSample) -> EligibilityResult:
    """Apply pre-declared global gates without running an estimator."""
    if EVIDENCE_SPECS.get(spec.key) != spec:
        raise ValueError(f"Eligibility requires the registered specification: {spec.key}")
    n = len(sample.rows)
    dependent_names = [item.name for item in spec.inputs if item.role == "dependent"]
    focal_names = [item.name for item in spec.inputs if item.role == "focal"]
    explanatory_names = [
        item.name for item in spec.inputs if item.role in {"focal", "control"}
    ]
    dependent_variation = all(
        _has_variation([row.values[name] for row in sample.rows])
        for name in dependent_names
    ) if sample.rows else False
    focal_variation = (
        all(
            _has_variation([row.values[name] for row in sample.rows])
            for name in focal_names
        )
        if focal_names
        else dependent_variation
    )
    residual_df = n - spec.fitted_parameter_count
    no_future_information = all(
        source_date <= row.date
        for row in sample.rows
        for source_date in row.source_dates.values()
    )
    if explanatory_names and sample.rows:
        columns = [
            [1.0 for _ in sample.rows],
            *[
                [row.values[name] for row in sample.rows]
                for name in explanatory_names
            ],
        ]
        no_exact_multicollinearity = _matrix_rank(columns) == len(columns)
    else:
        no_exact_multicollinearity = True

    checks = {
        "minimum_observations": n >= spec.minimum_observations,
        "minimum_complete_pairs": n >= spec.minimum_complete_pairs,
        "dependent_variation": dependent_variation,
        "focal_variation": focal_variation,
        "residual_degrees_of_freedom": (
            residual_df >= spec.minimum_residual_degrees_of_freedom
        ),
        "no_exact_multicollinearity": no_exact_multicollinearity,
        "no_future_information": no_future_information,
    }
    failed = [key for key, passed in checks.items() if not passed]
    eligible = not failed
    reason = (
        "All registered pre-estimation eligibility gates passed."
        if eligible
        else "Failed registered eligibility gates: " + ", ".join(failed) + "."
    )
    return EligibilityResult(
        eligible=eligible,
        required_observations=max(
            spec.minimum_observations,
            spec.minimum_complete_pairs,
            spec.fitted_parameter_count + spec.minimum_residual_degrees_of_freedom,
        ),
        available_observations=n,
        reason=reason,
        checks=checks,
    )


def insufficient_evidence_result(
    spec: EvidenceSpec,
    sample: AlignedSample,
    eligibility: EligibilityResult,
) -> EvidenceResult:
    """Turn a failed gate into a valid, publishable evidence result."""
    if eligibility.eligible:
        raise ValueError("Cannot create insufficient evidence from an eligible sample")
    return EvidenceResult(
        analysis_key=spec.key,
        status=EvidenceStatus.INSUFFICIENT_DATA,
        grade=EvidenceGrade.NOT_ASSESSED,
        sample_size=len(sample.rows),
        start_date=sample.start_date,
        end_date=sample.end_date,
        estimates=(),
        diagnostics=(),
        robustness=(),
        practical_interpretation=(
            "The registered analysis was not estimated because its pre-declared "
            "eligibility requirements were not met."
        ),
        limitation=spec.limitation,
        exclusion_summary=sample.excluded,
        eligibility=eligibility,
    )
