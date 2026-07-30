"""Execute only the frozen version-1 evidence specifications."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date
import math
from typing import Sequence

from statsmodels.stats.multitest import multipletests

from config.evidence_specs import EVIDENCE_SPECS, EvidenceSpec, ExpectedDirection
from models import (
    DiagnosticResult,
    Estimate,
    EvidenceGrade,
    EvidenceResult,
    EvidenceStatus,
    RobustnessResult,
)

from .alignment import AlignedRow
from .eligibility import insufficient_evidence_result
from .pipeline import PreparedAnalysis, prepare_registered_analysis
from .regression import RegressionError, RegressionFit, fit_ols_hac


_CONFIDENCE_LEVEL = 0.95


def _calendar_month_index(value: date) -> int:
    return value.year * 12 + value.month


def _direction_matches(spec: EvidenceSpec, value: float) -> bool:
    if spec.expected_direction is ExpectedDirection.POSITIVE:
        return value > 0
    if spec.expected_direction is ExpectedDirection.NEGATIVE:
        return value < 0
    return value != 0


def _transform_value(value: float, transformation: str) -> float:
    if transformation == "identity":
        return value
    if transformation == "annual_log_percent":
        return 100.0 * math.expm1(12.0 * value)
    if transformation == "annual_level":
        return 12.0 * value
    if transformation == "log_percent":
        return 100.0 * math.expm1(value)
    raise ValueError(f"Unknown estimate transformation: {transformation}")


def _transformed_standard_error(
    coefficient: float,
    standard_error: float,
    transformation: str,
) -> float:
    if transformation == "identity":
        return standard_error
    if transformation == "annual_log_percent":
        return abs(1200.0 * math.exp(12.0 * coefficient) * standard_error)
    if transformation == "annual_level":
        return 12.0 * standard_error
    if transformation == "log_percent":
        return abs(100.0 * math.exp(coefficient) * standard_error)
    raise ValueError(f"Unknown estimate transformation: {transformation}")


def _estimate_from_fit(
    fit: RegressionFit,
    fitted_term: str,
    *,
    output_term: str,
    unit: str,
    is_focal: bool,
    transformation: str = "identity",
) -> Estimate:
    coefficient = fit.coefficient(fitted_term)
    interval_low, interval_high = fit.confidence_interval(fitted_term)
    return Estimate(
        term=output_term,
        value=_transform_value(coefficient, transformation),
        unit=unit,
        is_focal=is_focal,
        standard_error=_transformed_standard_error(
            coefficient,
            fit.standard_error(fitted_term),
            transformation,
        ),
        confidence_level=_CONFIDENCE_LEVEL,
        confidence_interval_low=_transform_value(interval_low, transformation),
        confidence_interval_high=_transform_value(interval_high, transformation),
        p_value=fit.p_value(fitted_term),
        adjusted_p_value=None,
    )


def _fiscal_design(
    spec: EvidenceSpec,
    rows: Sequence[AlignedRow],
    *,
    parsimonious: bool = False,
    omit_exceptional_indicator: bool = False,
) -> tuple[list[float], list[list[float]], tuple[str, ...]]:
    if not rows:
        raise RegressionError("Fiscal regression has no observations")
    if spec.key == "debt-interest-burden-change":
        dependent_name = "interest_burden_change"
        focal_name = "lagged_general_government_debt"
        if parsimonious:
            terms = ("intercept", focal_name)
        else:
            terms = (
                "intercept",
                focal_name,
                "lagged_primary_balance",
                "trend",
            )
        design = []
        first_year = rows[0].date.year
        for row in rows:
            values = [1.0, row.values[focal_name]]
            if not parsimonious:
                values.extend([
                    row.values["lagged_primary_balance"],
                    float(row.date.year - first_year),
                ])
            design.append(values)
    elif spec.key == "primary-balance-debt-change":
        dependent_name = "debt_change"
        focal_name = "lagged_primary_balance"
        if parsimonious:
            terms = ("intercept", focal_name)
        elif omit_exceptional_indicator:
            terms = (
                "intercept",
                focal_name,
                "lagged_debt_change",
            )
        else:
            terms = (
                "intercept",
                focal_name,
                "lagged_debt_change",
                "covid_fy2020_22",
            )
        design = []
        for row in rows:
            values = [1.0, row.values[focal_name]]
            if not parsimonious:
                values.append(row.values["lagged_debt_change"])
                if not omit_exceptional_indicator:
                    values.append(
                        1.0
                        if row.date in {date(2021, 3, 31), date(2022, 3, 31)}
                        else 0.0
                    )
            design.append(values)
    else:
        raise RegressionError(f"Not a registered fiscal estimator: {spec.key}")
    return (
        [row.values[dependent_name] for row in rows],
        design,
        terms,
    )


def _upi_design(
    spec: EvidenceSpec,
    rows: Sequence[AlignedRow],
    *,
    level: bool = False,
) -> tuple[list[float], list[list[float]], tuple[str, ...]]:
    if not rows or spec.break_date is None:
        raise RegressionError("UPI regression lacks observations or its registered break")
    dependent_name = "log_upi_transactions_per_capita"
    first_month = _calendar_month_index(rows[0].date)
    break_month = _calendar_month_index(spec.break_date)
    terms = (
        "intercept",
        "monthly_log_trend" if not level else "monthly_level_trend",
        *(f"month_{month:02d}" for month in range(2, 13)),
        "covid_level",
        "post_covid_slope",
    )
    design: list[list[float]] = []
    dependent: list[float] = []
    for row in rows:
        month_index = _calendar_month_index(row.date)
        values = [
            1.0,
            float(month_index - first_month),
            *(1.0 if row.date.month == month else 0.0 for month in range(2, 13)),
            1.0 if month_index >= break_month else 0.0,
            float(max(0, month_index - break_month)),
        ]
        design.append(values)
        logged_value = row.values[dependent_name]
        dependent.append(math.exp(logged_value) if level else logged_value)
    return dependent, design, terms


def _fit_fiscal(
    spec: EvidenceSpec,
    rows: Sequence[AlignedRow],
    *,
    max_lags: int,
    parsimonious: bool = False,
    omit_exceptional_indicator: bool = False,
) -> RegressionFit:
    dependent, design, terms = _fiscal_design(
        spec,
        rows,
        parsimonious=parsimonious,
        omit_exceptional_indicator=omit_exceptional_indicator,
    )
    return fit_ols_hac(dependent, design, terms, max_lags=max_lags)


def _fit_upi(
    spec: EvidenceSpec,
    rows: Sequence[AlignedRow],
    *,
    max_lags: int,
    level: bool = False,
) -> RegressionFit:
    dependent, design, terms = _upi_design(spec, rows, level=level)
    return fit_ols_hac(dependent, design, terms, max_lags=max_lags)


def _fiscal_focal_estimate(spec: EvidenceSpec, fit: RegressionFit) -> Estimate:
    term = spec.focal_terms[0]
    unit = (
        "interest_burden_percentage_point_change_per_debt_percentage_point"
        if spec.key == "debt-interest-burden-change"
        else "debt_percentage_point_change_per_primary_balance_percentage_point"
    )
    return _estimate_from_fit(
        fit,
        term,
        output_term=term,
        unit=unit,
        is_focal=True,
    )


def _upi_focal_estimate(
    fit: RegressionFit,
    *,
    level: bool = False,
) -> Estimate:
    return _estimate_from_fit(
        fit,
        "monthly_level_trend" if level else "monthly_log_trend",
        output_term="annualised_underlying_trend",
        unit=(
            "transactions_per_person_per_year"
            if level
            else "percent_per_year"
        ),
        is_focal=True,
        transformation="annual_level" if level else "annual_log_percent",
    )


def _diagnostics(
    spec: EvidenceSpec,
    fit: RegressionFit,
    *,
    stability_passed: bool | None = None,
) -> tuple[DiagnosticResult, ...]:
    cook_max = max(fit.cooks_distances)
    diagnostic_by_key = {
        "residual_degrees_of_freedom": DiagnosticResult(
            key="residual_degrees_of_freedom",
            value=fit.residual_degrees_of_freedom,
            threshold=float(spec.minimum_residual_degrees_of_freedom),
            passed=(
                fit.residual_degrees_of_freedom
                >= spec.minimum_residual_degrees_of_freedom
            ),
            interpretation=(
                "Residual degrees of freedom must meet the registered minimum."
            ),
        ),
        "condition_number": DiagnosticResult(
            key="condition_number",
            value=fit.condition_number,
            threshold=30.0,
            passed=fit.condition_number <= 30.0,
            interpretation=(
                "Condition number of the design after standardising every "
                "non-constant column; values above 30 fail the registered gate."
            ),
        ),
        "residual_autocorrelation": DiagnosticResult(
            key="residual_autocorrelation",
            value=fit.breusch_godfrey_p_value,
            threshold=0.01,
            passed=(
                fit.breusch_godfrey_p_value is not None
                and fit.breusch_godfrey_p_value >= 0.01
            ),
            interpretation=(
                "Breusch–Godfrey LM p-value at the registered HAC lag; "
                "values below 0.01 indicate residual serial dependence."
            ),
        ),
        "stationarity": DiagnosticResult(
            key="stationarity",
            value=fit.adf_p_value,
            threshold=0.10,
            passed=fit.adf_p_value is not None and fit.adf_p_value < 0.10,
            interpretation=(
                "Augmented Dickey–Fuller residual p-value with no deterministic "
                "term and AIC lag selection; values below 0.10 pass."
            ),
        ),
        "influential_observation": DiagnosticResult(
            key="influential_observation",
            value=cook_max,
            threshold=1.0,
            passed=cook_max <= 1.0,
            interpretation=(
                f"Maximum Cook's distance; 1.0 is the hard gate and "
                f"4/n={4.0 / len(fit.residuals):.4f} is the screening reference."
            ),
        ),
        "stability": DiagnosticResult(
            key="stability",
            value=stability_passed,
            threshold=None,
            passed=stability_passed is True,
            interpretation=(
                "The registered focal direction must persist after separately "
                "dropping the first and last 12 observations."
            ),
        ),
    }
    return tuple(diagnostic_by_key[key] for key in spec.diagnostics)


def _robustness_status(spec: EvidenceSpec, estimate: Estimate) -> EvidenceStatus:
    return (
        EvidenceStatus.SUPPORTED
        if (
            estimate.p_value is not None
            and estimate.p_value < spec.alpha
            and _direction_matches(spec, estimate.value)
        )
        else EvidenceStatus.NOT_SUPPORTED
    )


def _failed_robustness(key: str, sample_size: int, error: Exception) -> RobustnessResult:
    return RobustnessResult(
        specification=key,
        status=EvidenceStatus.INSUFFICIENT_DATA,
        focal_estimate=None,
        sample_size=sample_size,
        note=f"Registered robustness fit could not be estimated: {error}",
    )


def _fiscal_robustness(
    prepared: PreparedAnalysis,
    main_fit: RegressionFit,
) -> tuple[RobustnessResult, ...]:
    spec = prepared.spec
    rows = list(prepared.sample.rows)
    output: list[RobustnessResult] = []
    for key in spec.robustness:
        variant_rows = rows
        max_lags = spec.covariance_max_lags
        parsimonious = False
        omit_exceptional_indicator = False
        note = ""
        if key == "exclude_covid_fiscal_years":
            variant_rows = [
                row
                for row in rows
                if row.date not in {date(2021, 3, 31), date(2022, 3, 31)}
            ]
            note = "Omitted the two registered COVID fiscal-year endpoints."
            omit_exceptional_indicator = (
                spec.key == "primary-balance-debt-change"
            )
        elif key == "actual_status_only":
            variant_rows = [
                row
                for row in rows
                if all(status.value == "actual" for status in row.statuses.values())
            ]
            note = "Retained rows for which every registered input is actual."
        elif key == "hac_max_lags_1":
            max_lags = 1
            note = "Used Newey–West HAC covariance with maximum lag one."
        elif key == "exclude_most_influential":
            influential = main_fit.most_influential_index
            variant_rows = [
                row for index, row in enumerate(rows) if index != influential
            ]
            note = f"Omitted the maximum-Cook-distance row dated {rows[influential].date}."
        elif key == "parsimonious_bivariate":
            parsimonious = True
            note = "Used an intercept and the registered focal regressor only."
        else:
            raise RegressionError(f"Unimplemented registered fiscal robustness: {key}")
        try:
            fit = _fit_fiscal(
                spec,
                variant_rows,
                max_lags=max_lags,
                parsimonious=parsimonious,
                omit_exceptional_indicator=omit_exceptional_indicator,
            )
            estimate = _fiscal_focal_estimate(spec, fit)
            output.append(RobustnessResult(
                specification=key,
                status=_robustness_status(spec, estimate),
                focal_estimate=estimate,
                sample_size=len(variant_rows),
                note=note,
            ))
        except RegressionError as exc:
            output.append(_failed_robustness(key, len(variant_rows), exc))
    return tuple(output)


def _upi_robustness(
    prepared: PreparedAnalysis,
) -> tuple[RobustnessResult, ...]:
    spec = prepared.spec
    rows = list(prepared.sample.rows)
    output: list[RobustnessResult] = []
    for key in spec.robustness:
        variant_rows = rows
        max_lags = spec.covariance_max_lags
        level = False
        note = ""
        if key == "start_date_2018_04":
            variant_rows = [row for row in rows if row.date >= date(2018, 4, 30)]
            note = "Moved the registered start date to April 2018."
        elif key == "exclude_pandemic_disruption_months":
            variant_rows = [
                row
                for row in rows
                if not date(2020, 3, 31) <= row.date <= date(2020, 6, 30)
            ]
            note = "Omitted March through June 2020."
        elif key == "linear_level_trend":
            level = True
            note = "Estimated the registered design in transactions-per-person levels."
        elif key == "hac_max_lags_6":
            max_lags = 6
            note = "Used Newey–West HAC covariance with maximum lag six."
        else:
            raise RegressionError(f"Unimplemented registered UPI robustness: {key}")
        try:
            fit = _fit_upi(
                spec,
                variant_rows,
                max_lags=max_lags,
                level=level,
            )
            estimate = _upi_focal_estimate(fit, level=level)
            output.append(RobustnessResult(
                specification=key,
                status=_robustness_status(spec, estimate),
                focal_estimate=estimate,
                sample_size=len(variant_rows),
                note=note,
            ))
        except RegressionError as exc:
            output.append(_failed_robustness(key, len(variant_rows), exc))
    return tuple(output)


def _estimate_fiscal(prepared: PreparedAnalysis) -> EvidenceResult:
    spec = prepared.spec
    rows = prepared.sample.rows
    fit = _fit_fiscal(spec, rows, max_lags=spec.covariance_max_lags)
    if len(fit.term_names) != spec.fitted_parameter_count:
        raise RegressionError(f"Fiscal design parameter count drifted: {spec.key}")
    focal = _fiscal_focal_estimate(spec, fit)
    estimates = [focal]
    if spec.key == "debt-interest-burden-change":
        estimates.extend([
            _estimate_from_fit(
                fit,
                "lagged_primary_balance",
                output_term="lagged_primary_balance",
                unit="interest_burden_percentage_point_change_per_primary_balance_percentage_point",
                is_focal=False,
            ),
            _estimate_from_fit(
                fit,
                "trend",
                output_term="trend",
                unit="interest_burden_percentage_point_change_per_year",
                is_focal=False,
            ),
        ])
    else:
        estimates.extend([
            _estimate_from_fit(
                fit,
                "lagged_debt_change",
                output_term="lagged_debt_change",
                unit="debt_percentage_point_change_per_prior_debt_change_percentage_point",
                is_focal=False,
            ),
            _estimate_from_fit(
                fit,
                "covid_fy2020_22",
                output_term="covid_fy2020_22",
                unit="debt_percentage_point_change",
                is_focal=False,
            ),
        ])
    return EvidenceResult(
        analysis_key=spec.key,
        status=EvidenceStatus.MIXED,
        grade=EvidenceGrade.LIMITED,
        sample_size=len(rows),
        start_date=prepared.sample.start_date,
        end_date=prepared.sample.end_date,
        estimates=tuple(estimates),
        diagnostics=_diagnostics(spec, fit),
        robustness=_fiscal_robustness(prepared, fit),
        practical_interpretation="Pending registered family adjustment and grading.",
        limitation="Inference and grading follow decision 0002.",
        exclusion_summary=prepared.sample.excluded,
        eligibility=prepared.eligibility,
    )


def _upi_stability(spec: EvidenceSpec, rows: Sequence[AlignedRow]) -> bool:
    if len(rows) <= 36:
        return False
    variants = (rows[12:], rows[:-12])
    try:
        return all(
            _direction_matches(
                spec,
                _upi_focal_estimate(
                    _fit_upi(
                        spec,
                        variant,
                        max_lags=spec.covariance_max_lags,
                    )
                ).value,
            )
            for variant in variants
        )
    except RegressionError:
        return False


def _estimate_upi(prepared: PreparedAnalysis) -> EvidenceResult:
    spec = prepared.spec
    rows = prepared.sample.rows
    fit = _fit_upi(spec, rows, max_lags=spec.covariance_max_lags)
    if len(fit.term_names) != spec.fitted_parameter_count:
        raise RegressionError("UPI design parameter count drifted")
    estimates = (
        _upi_focal_estimate(fit),
        _estimate_from_fit(
            fit,
            "covid_level",
            output_term="covid_level_shift",
            unit="percent",
            is_focal=False,
            transformation="log_percent",
        ),
        _estimate_from_fit(
            fit,
            "post_covid_slope",
            output_term="annualised_post_covid_slope_change",
            unit="percent_per_year",
            is_focal=False,
            transformation="annual_log_percent",
        ),
    )
    return EvidenceResult(
        analysis_key=spec.key,
        status=EvidenceStatus.MIXED,
        grade=EvidenceGrade.LIMITED,
        sample_size=len(rows),
        start_date=prepared.sample.start_date,
        end_date=prepared.sample.end_date,
        estimates=estimates,
        diagnostics=_diagnostics(
            spec,
            fit,
            stability_passed=_upi_stability(spec, rows),
        ),
        robustness=_upi_robustness(prepared),
        practical_interpretation="Pending registered family adjustment and grading.",
        limitation="Inference and grading follow decision 0002.",
        exclusion_summary=prepared.sample.excluded,
        eligibility=prepared.eligibility,
    )


def _draft_result(prepared: PreparedAnalysis) -> EvidenceResult:
    if not prepared.eligibility.eligible:
        return insufficient_evidence_result(
            prepared.spec,
            prepared.sample,
            prepared.eligibility,
        )
    if prepared.spec.lens_key == "fiscal_capacity":
        return _estimate_fiscal(prepared)
    if prepared.spec.key == "upi-adoption-trend":
        return _estimate_upi(prepared)
    raise RegressionError(f"No registered estimator for {prepared.spec.key}")


def _adjust_focal_p_values(
    results: Sequence[EvidenceResult],
) -> tuple[EvidenceResult, ...]:
    result_by_key = {result.analysis_key: result for result in results}
    families: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
    for spec in EVIDENCE_SPECS.values():
        result = result_by_key[spec.key]
        focal_by_term = {
            estimate.term: (index, estimate)
            for index, estimate in enumerate(result.estimates)
            if estimate.is_focal
        }
        for term in spec.focal_terms:
            if result.status is EvidenceStatus.INSUFFICIENT_DATA:
                families[spec.multiple_testing_family].append((spec.key, -1, 1.0))
            else:
                index, estimate = focal_by_term[term]
                families[spec.multiple_testing_family].append(
                    (spec.key, index, float(estimate.p_value))
                )

    for members in families.values():
        adjusted = multipletests(
            [member[2] for member in members],
            alpha=0.05,
            method="fdr_bh",
        )[1]
        for (analysis_key, estimate_index, _), adjusted_p_value in zip(
            members,
            adjusted,
        ):
            if estimate_index < 0:
                continue
            result = result_by_key[analysis_key]
            estimates = list(result.estimates)
            estimates[estimate_index] = replace(
                estimates[estimate_index],
                adjusted_p_value=float(adjusted_p_value),
            )
            result_by_key[analysis_key] = replace(
                result,
                estimates=tuple(estimates),
            )
    return tuple(result_by_key[key] for key in EVIDENCE_SPECS)


def _interpretation(
    spec: EvidenceSpec,
    result: EvidenceResult,
    status: EvidenceStatus,
) -> str:
    focal = next(estimate for estimate in result.estimates if estimate.is_focal)
    interval = (
        f"{focal.confidence_interval_low:.3f} to "
        f"{focal.confidence_interval_high:.3f}"
    )
    expected_direction = {
        ExpectedDirection.POSITIVE: "positive",
        ExpectedDirection.NEGATIVE: "negative",
        ExpectedDirection.TWO_SIDED: "non-zero",
    }[spec.expected_direction]
    failed_diagnostics = [
        item.key for item in result.diagnostics if item.passed is False
    ]
    evidence_phrase = {
        EvidenceStatus.SUPPORTED: "met the registered support and robustness rules",
        EvidenceStatus.NOT_SUPPORTED: (
            "did not meet the registered support rule "
            f"(expected focal direction: {expected_direction})"
        ),
        EvidenceStatus.MIXED: "produced mixed main-model and robustness evidence",
        EvidenceStatus.FAILED_DIAGNOSTICS: (
            "failed the registered model diagnostic"
            f"{'s' if len(failed_diagnostics) != 1 else ''}: "
            + ", ".join(failed_diagnostics)
        ),
    }[status]
    if spec.key == "upi-adoption-trend":
        return (
            f"The registered model estimated an annualised underlying UPI trend "
            f"of {focal.value:.3f}% (95% interval {interval}; "
            f"Benjamini–Hochberg-adjusted p={focal.adjusted_p_value:.4g}) and "
            f"{evidence_phrase}. This describes observed adoption over time and "
            f"does not identify a policy effect."
        )
    subject = (
        "one percentage point higher lagged general-government debt"
        if spec.key == "debt-interest-burden-change"
        else "one percentage point stronger lagged primary balance"
    )
    outcome = (
        "the subsequent interest-burden change"
        if spec.key == "debt-interest-burden-change"
        else "the subsequent general-government debt change"
    )
    return (
        f"Within the registered observational model, {subject} was associated "
        f"with an estimated {focal.value:.3f} percentage-point difference in "
        f"{outcome} (95% interval {interval}; "
        f"Benjamini–Hochberg-adjusted p={focal.adjusted_p_value:.4g}). The result "
        f"{evidence_phrase}."
    )


def _finalise_result(result: EvidenceResult) -> EvidenceResult:
    if result.status is EvidenceStatus.INSUFFICIENT_DATA:
        return result
    spec = EVIDENCE_SPECS[result.analysis_key]
    focal = [estimate for estimate in result.estimates if estimate.is_focal]
    main_support = all(
        estimate.adjusted_p_value is not None
        and estimate.adjusted_p_value < spec.alpha
        and _direction_matches(spec, estimate.value)
        for estimate in focal
    )
    failed_diagnostics = any(
        diagnostic.passed is False for diagnostic in result.diagnostics
    )
    estimable_robustness = [
        item for item in result.robustness if item.focal_estimate is not None
    ]
    supported_robustness = [
        item
        for item in estimable_robustness
        if item.status is EvidenceStatus.SUPPORTED
    ]
    all_directionally_consistent = (
        len(estimable_robustness) == len(result.robustness)
        and all(
            _direction_matches(spec, item.focal_estimate.value)
            for item in estimable_robustness
        )
    )
    if failed_diagnostics:
        status = EvidenceStatus.FAILED_DIAGNOSTICS
    elif main_support:
        status = (
            EvidenceStatus.SUPPORTED
            if (
                all_directionally_consistent
                and len(supported_robustness) >= math.ceil(len(result.robustness) / 2)
            )
            else EvidenceStatus.MIXED
        )
    elif supported_robustness:
        status = EvidenceStatus.MIXED
    else:
        status = EvidenceStatus.NOT_SUPPORTED

    grade = (
        EvidenceGrade.STRONG
        if (
            status is EvidenceStatus.SUPPORTED
            and len(supported_robustness) == len(result.robustness)
        )
        else EvidenceGrade.MODERATE
        if status is EvidenceStatus.SUPPORTED
        else EvidenceGrade.LIMITED
    )
    return replace(
        result,
        status=status,
        grade=grade,
        practical_interpretation=_interpretation(spec, result, status),
        limitation=(
            "Inference and deterministic grading follow decision 0002. "
            f"{len(supported_robustness)} of {len(result.robustness)} registered "
            "robustness fits met their unadjusted directional support rule."
        ),
    )


def estimate_registered_evidence() -> tuple[
    tuple[PreparedAnalysis, ...],
    tuple[EvidenceResult, ...],
]:
    """Prepare, estimate, adjust and grade every registered version-1 analysis."""
    prepared = tuple(
        prepare_registered_analysis(analysis_key)
        for analysis_key in EVIDENCE_SPECS
    )
    drafts = tuple(_draft_result(item) for item in prepared)
    adjusted = _adjust_focal_p_values(drafts)
    results = tuple(_finalise_result(result) for result in adjusted)
    return prepared, results
