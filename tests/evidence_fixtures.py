"""Synthetic evidence objects used only to test publication contracts."""

from __future__ import annotations

from datetime import date

from builders import build_evidence_report
from models import (
    DiagnosticResult,
    EligibilityResult,
    Estimate,
    EvidenceGrade,
    EvidenceResult,
    EvidenceStatus,
    RobustnessResult,
    SourceAsset,
)
from config.evidence_specs import EVIDENCE_SPECS


SOURCE_ASSET = SourceAsset(
    path="digital-integration/upi-and-tax-capacity.json",
    contract="dated_multi_series",
    sha256="1" * 64,
    generated_at="2026-07-28T10:00:00+00:00",
    start_date=date(2016, 4, 30),
    end_date=date(2026, 6, 30),
)


def supported_result() -> EvidenceResult:
    spec = EVIDENCE_SPECS["upi-adoption-trend"]
    robustness_estimate = Estimate(
        term="annualised_underlying_trend",
        value=0.09,
        unit="synthetic_log_points_per_month",
        is_focal=True,
        standard_error=0.025,
        confidence_level=0.95,
        confidence_interval_low=0.04,
        confidence_interval_high=0.14,
        p_value=0.02,
    )
    return EvidenceResult(
        analysis_key="upi-adoption-trend",
        status=EvidenceStatus.SUPPORTED,
        grade=EvidenceGrade.MODERATE,
        sample_size=60,
        start_date=date(2019, 1, 31),
        end_date=date(2023, 12, 31),
        estimates=(
            Estimate(
                term="annualised_underlying_trend",
                value=0.1,
                unit="synthetic_log_points_per_month",
                is_focal=True,
                standard_error=0.02,
                confidence_level=0.95,
                confidence_interval_low=0.06,
                confidence_interval_high=0.14,
                p_value=0.01,
                adjusted_p_value=0.02,
            ),
        ),
        diagnostics=tuple(
            DiagnosticResult(
                key=key,
                value=True,
                threshold=None,
                passed=True,
                interpretation="Synthetic diagnostic fixture passed.",
            )
            for key in spec.diagnostics
        ),
        robustness=tuple(
            RobustnessResult(
                specification=key,
                status=EvidenceStatus.SUPPORTED,
                focal_estimate=robustness_estimate,
                sample_size=58,
                note="Synthetic robustness fixture; not a project finding.",
            )
            for key in spec.robustness
        ),
        practical_interpretation="Synthetic fixture: the registered measure is associated with a positive trend.",
        limitation="Synthetic contract fixture; this is not a project finding.",
        exclusion_summary={"missing_value": 2},
        eligibility=EligibilityResult(
            True,
            36,
            60,
            "Synthetic fixture passed registered gates.",
            {"minimum_observations": True},
        ),
    )


def descriptive_result() -> EvidenceResult:
    return EvidenceResult(
        analysis_key="upi-adoption-trend",
        status=EvidenceStatus.DESCRIPTIVE_ONLY,
        grade=EvidenceGrade.DESCRIPTIVE,
        sample_size=24,
        start_date=date(2019, 1, 31),
        end_date=date(2020, 12, 31),
        estimates=(
            Estimate(
                term="synthetic_change",
                value=1.5,
                unit="synthetic_transactions_per_person",
                is_focal=False,
            ),
        ),
        practical_interpretation="Synthetic fixture: the observed measure increased over the stated sample.",
        limitation="Descriptive contract fixture without an uncertainty model.",
        exclusion_summary={},
    )


def insufficient_result() -> EvidenceResult:
    return EvidenceResult(
        analysis_key="upi-adoption-trend",
        status=EvidenceStatus.INSUFFICIENT_DATA,
        grade=EvidenceGrade.NOT_ASSESSED,
        sample_size=20,
        start_date=date(2019, 1, 31),
        end_date=date(2020, 8, 31),
        estimates=(),
        practical_interpretation="The synthetic analysis was not estimated because coverage is insufficient.",
        limitation="At least 36 observations are required.",
        exclusion_summary={"missing_value": 4},
        eligibility=EligibilityResult(
            False,
            36,
            20,
            "The synthetic fixture has too few observations.",
            {"minimum_observations": False},
        ),
    )


def digital_report(result: EvidenceResult) -> dict:
    return build_evidence_report(
        "digital_integration",
        (result,),
        source_assets=(SOURCE_ASSET,),
        code_version="synthetic-test-version",
        software_versions={"python": "test"},
    )
