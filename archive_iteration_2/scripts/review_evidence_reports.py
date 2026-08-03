"""Independently reproduce main evidence results and decision-state grading."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path

import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_breusch_godfrey
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import adfuller

from analysis import prepare_registered_analysis
from config import PROJECT_ROOT
from config.evidence_specs import EVIDENCE_OUTPUT_PATHS, EVIDENCE_SPECS


@dataclass(frozen=True, slots=True)
class DirectFit:
    base: object
    robust: object
    design: np.ndarray
    focal_index: int


def _month_index(value: date) -> int:
    return value.year * 12 + value.month


def _design(analysis_key: str, rows) -> tuple[np.ndarray, np.ndarray, int]:
    if analysis_key == "debt-interest-burden-change":
        first_year = rows[0].date.year
        y = [row.values["interest_burden_change"] for row in rows]
        x = [
            [
                1.0,
                row.values["lagged_general_government_debt"],
                row.values["lagged_primary_balance"],
                float(row.date.year - first_year),
            ]
            for row in rows
        ]
    elif analysis_key == "primary-balance-debt-change":
        y = [row.values["debt_change"] for row in rows]
        x = [
            [
                1.0,
                row.values["lagged_primary_balance"],
                row.values["lagged_debt_change"],
                (
                    1.0
                    if row.date in {date(2021, 3, 31), date(2022, 3, 31)}
                    else 0.0
                ),
            ]
            for row in rows
        ]
    elif analysis_key == "upi-adoption-trend":
        spec = EVIDENCE_SPECS[analysis_key]
        first_month = _month_index(rows[0].date)
        break_month = _month_index(spec.break_date)
        y = [row.values["log_upi_transactions_per_capita"] for row in rows]
        x = []
        for row in rows:
            current_month = _month_index(row.date)
            x.append([
                1.0,
                float(current_month - first_month),
                *(1.0 if row.date.month == month else 0.0 for month in range(2, 13)),
                1.0 if current_month >= break_month else 0.0,
                float(max(0, current_month - break_month)),
            ])
    else:
        raise ValueError(f"No independent review design for {analysis_key}")
    return np.asarray(y, dtype=float), np.asarray(x, dtype=float), 1


def _fit(analysis_key: str, rows) -> DirectFit:
    spec = EVIDENCE_SPECS[analysis_key]
    y, x, focal_index = _design(analysis_key, rows)
    base = sm.OLS(y, x, hasconst=True).fit()
    robust = base.get_robustcov_results(
        cov_type="HAC",
        maxlags=spec.covariance_max_lags,
        kernel="bartlett",
        use_correction=True,
        use_t=True,
    )
    return DirectFit(base, robust, x, focal_index)


def _transform(analysis_key: str, value: float) -> float:
    return (
        100.0 * math.expm1(12.0 * value)
        if analysis_key == "upi-adoption-trend"
        else value
    )


def _condition_number(design: np.ndarray) -> float:
    scaled = design.copy()
    for column in range(scaled.shape[1]):
        standard_deviation = float(np.std(scaled[:, column]))
        if standard_deviation > 0:
            scaled[:, column] = (
                scaled[:, column] - float(np.mean(scaled[:, column]))
            ) / standard_deviation
    return float(np.linalg.cond(scaled))


def _diagnostics(analysis_key: str, rows, fit: DirectFit) -> dict[str, tuple[object, bool]]:
    spec = EVIDENCE_SPECS[analysis_key]
    n = len(rows)
    k = fit.design.shape[1]
    diagnostic_lags = min(
        max(1, spec.covariance_max_lags),
        max(1, n - k - 1),
    )
    bg_p = float(acorr_breusch_godfrey(fit.base, nlags=diagnostic_lags)[1])
    adf_p = float(adfuller(fit.base.resid, regression="n", autolag="AIC")[1])
    cook_max = float(np.max(fit.base.get_influence().cooks_distance[0]))
    output: dict[str, tuple[object, bool]] = {
        "residual_degrees_of_freedom": (
            int(fit.base.df_resid),
            int(fit.base.df_resid) >= spec.minimum_residual_degrees_of_freedom,
        ),
        "condition_number": (
            _condition_number(fit.design),
            _condition_number(fit.design) <= 30.0,
        ),
        "residual_autocorrelation": (bg_p, bg_p >= 0.01),
        "stationarity": (adf_p, adf_p < 0.10),
        "influential_observation": (cook_max, cook_max <= 1.0),
    }
    if "stability" in spec.diagnostics:
        direction_values = [
            float(_fit(analysis_key, variant).robust.params[1])
            for variant in (rows[12:], rows[:-12])
        ]
        stability = all(value > 0 for value in direction_values)
        output["stability"] = (stability, stability)
    return output


def _close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9):
        raise AssertionError(f"{label}: published {actual}, reproduced {expected}")


def review_reports() -> list[dict]:
    reports = {}
    for lens_key in {spec.lens_key for spec in EVIDENCE_SPECS.values()}:
        path = PROJECT_ROOT / "data" / "processed" / EVIDENCE_OUTPUT_PATHS[lens_key]
        reports[lens_key] = json.loads(path.read_text(encoding="utf-8"))
    published = {
        analysis["analysis_key"]: analysis
        for report in reports.values()
        for analysis in report["analyses"]
    }

    raw_p_values: dict[str, float] = {}
    reproduced: dict[str, dict] = {}
    for analysis_key, spec in EVIDENCE_SPECS.items():
        prepared = prepare_registered_analysis(analysis_key)
        rows = prepared.sample.rows
        fit = _fit(analysis_key, rows)
        report_analysis = published[analysis_key]
        report_focal = next(
            estimate
            for estimate in report_analysis["estimates"]
            if estimate["is_focal"]
        )
        coefficient = float(fit.robust.params[fit.focal_index])
        interval = fit.robust.conf_int(alpha=0.05)[fit.focal_index]
        focal_value = _transform(analysis_key, coefficient)
        interval_low = _transform(analysis_key, float(interval[0]))
        interval_high = _transform(analysis_key, float(interval[1]))
        raw_p = float(fit.robust.pvalues[fit.focal_index])
        _close(report_focal["value"], focal_value, f"{analysis_key}/estimate")
        _close(
            report_focal["confidence_interval"][0],
            interval_low,
            f"{analysis_key}/ci-low",
        )
        _close(
            report_focal["confidence_interval"][1],
            interval_high,
            f"{analysis_key}/ci-high",
        )
        _close(report_focal["p_value"], raw_p, f"{analysis_key}/p-value")

        direct_diagnostics = _diagnostics(analysis_key, rows, fit)
        for diagnostic in report_analysis["diagnostics"]:
            direct_value, direct_passed = direct_diagnostics[diagnostic["key"]]
            if isinstance(direct_value, bool):
                if diagnostic["value"] is not direct_value:
                    raise AssertionError(f"{analysis_key}/{diagnostic['key']} value drift")
            else:
                _close(
                    float(diagnostic["value"]),
                    float(direct_value),
                    f"{analysis_key}/{diagnostic['key']}",
                )
            if diagnostic["passed"] is not direct_passed:
                raise AssertionError(f"{analysis_key}/{diagnostic['key']} flag drift")

        raw_p_values[analysis_key] = raw_p
        reproduced[analysis_key] = {
            "focal_value": focal_value,
            "diagnostics": direct_diagnostics,
        }

    families: dict[str, list[str]] = defaultdict(list)
    for analysis_key, spec in EVIDENCE_SPECS.items():
        families[spec.multiple_testing_family].append(analysis_key)
    for members in families.values():
        adjusted = multipletests(
            [raw_p_values[key] for key in members],
            alpha=0.05,
            method="fdr_bh",
        )[1]
        for analysis_key, adjusted_p in zip(members, adjusted):
            focal = next(
                estimate
                for estimate in published[analysis_key]["estimates"]
                if estimate["is_focal"]
            )
            _close(
                focal["adjusted_p_value"],
                float(adjusted_p),
                f"{analysis_key}/adjusted-p",
            )

    review_rows = []
    for analysis_key, spec in EVIDENCE_SPECS.items():
        analysis = published[analysis_key]
        focal = next(item for item in analysis["estimates"] if item["is_focal"])
        direction_matches = (
            focal["value"] > 0
            if spec.expected_direction.value == "positive"
            else focal["value"] < 0
            if spec.expected_direction.value == "negative"
            else focal["value"] != 0
        )
        main_support = (
            focal["adjusted_p_value"] < spec.alpha and direction_matches
        )
        failed_diagnostics = [
            item["key"] for item in analysis["diagnostics"] if item["passed"] is False
        ]
        supported_robustness = []
        all_directionally_consistent = True
        for robustness in analysis["robustness"]:
            estimate = robustness["focal_estimate"]
            if estimate is None:
                all_directionally_consistent = False
                if robustness["status"] != "insufficient_data":
                    raise AssertionError(f"{analysis_key}/{robustness['specification']} status drift")
                continue
            robust_direction = (
                estimate["value"] > 0
                if spec.expected_direction.value == "positive"
                else estimate["value"] < 0
                if spec.expected_direction.value == "negative"
                else estimate["value"] != 0
            )
            expected_robust_status = (
                "supported"
                if estimate["p_value"] < spec.alpha and robust_direction
                else "not_supported"
            )
            if robustness["status"] != expected_robust_status:
                raise AssertionError(f"{analysis_key}/{robustness['specification']} status drift")
            all_directionally_consistent &= robust_direction
            if expected_robust_status == "supported":
                supported_robustness.append(robustness)

        if failed_diagnostics:
            expected_status = "failed_diagnostics"
        elif main_support:
            expected_status = (
                "supported"
                if (
                    all_directionally_consistent
                    and len(supported_robustness)
                    >= math.ceil(len(analysis["robustness"]) / 2)
                )
                else "mixed"
            )
        elif supported_robustness:
            expected_status = "mixed"
        else:
            expected_status = "not_supported"
        expected_grade = (
            "strong"
            if (
                expected_status == "supported"
                and len(supported_robustness) == len(analysis["robustness"])
            )
            else "moderate"
            if expected_status == "supported"
            else "limited"
        )
        if analysis["status"] != expected_status or analysis["grade"] != expected_grade:
            raise AssertionError(f"{analysis_key}: status/grade drift")
        review_rows.append({
            "analysis_key": analysis_key,
            "focal_value": reproduced[analysis_key]["focal_value"],
            "adjusted_p_value": focal["adjusted_p_value"],
            "failed_diagnostics": failed_diagnostics,
            "status": expected_status,
            "grade": expected_grade,
        })
    return review_rows


def main() -> None:
    print(json.dumps({"review": "passed", "analyses": review_reports()}, indent=2))


if __name__ == "__main__":
    main()
