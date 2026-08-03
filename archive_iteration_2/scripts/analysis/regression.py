"""Small, explicit statsmodels boundary for registered OLS/HAC evidence work."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_breusch_godfrey
from statsmodels.tsa.stattools import adfuller


class RegressionError(ValueError):
    """Raised when a registered design cannot be estimated safely."""


@dataclass(frozen=True, slots=True)
class RegressionFit:
    term_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    standard_errors: tuple[float, ...]
    p_values: tuple[float, ...]
    confidence_interval_low: tuple[float, ...]
    confidence_interval_high: tuple[float, ...]
    residuals: tuple[float, ...]
    fitted_values: tuple[float, ...]
    residual_degrees_of_freedom: int
    condition_number: float
    breusch_godfrey_p_value: float | None
    adf_p_value: float | None
    cooks_distances: tuple[float, ...]
    max_lags: int

    def index(self, term: str) -> int:
        try:
            return self.term_names.index(term)
        except ValueError as exc:
            raise RegressionError(f"Unknown fitted term: {term}") from exc

    def coefficient(self, term: str) -> float:
        return self.coefficients[self.index(term)]

    def standard_error(self, term: str) -> float:
        return self.standard_errors[self.index(term)]

    def p_value(self, term: str) -> float:
        return self.p_values[self.index(term)]

    def confidence_interval(self, term: str) -> tuple[float, float]:
        index = self.index(term)
        return (
            self.confidence_interval_low[index],
            self.confidence_interval_high[index],
        )

    @property
    def most_influential_index(self) -> int:
        return max(range(len(self.cooks_distances)), key=self.cooks_distances.__getitem__)


def _finite_tuple(values: np.ndarray, *, label: str) -> tuple[float, ...]:
    flattened = np.asarray(values, dtype=float).reshape(-1)
    if not np.isfinite(flattened).all():
        raise RegressionError(f"{label} contains a non-finite value")
    return tuple(float(value) for value in flattened)


def _standardised_condition_number(design: np.ndarray) -> float:
    scaled = design.astype(float, copy=True)
    for column in range(scaled.shape[1]):
        values = scaled[:, column]
        standard_deviation = float(np.std(values))
        if standard_deviation > 0:
            scaled[:, column] = (values - float(np.mean(values))) / standard_deviation
    condition = float(np.linalg.cond(scaled))
    if not math.isfinite(condition):
        raise RegressionError("Standardised design has a non-finite condition number")
    return condition


def fit_ols_hac(
    dependent: Sequence[float],
    design: Sequence[Sequence[float]],
    term_names: Sequence[str],
    *,
    max_lags: int,
) -> RegressionFit:
    """Fit OLS with registered Newey-West HAC covariance and t inference."""
    y = np.asarray(dependent, dtype=float)
    x = np.asarray(design, dtype=float)
    names = tuple(term_names)
    if y.ndim != 1 or x.ndim != 2 or x.shape[0] != y.shape[0]:
        raise RegressionError("Regression arrays have incompatible shapes")
    if x.shape[1] != len(names) or len(names) != len(set(names)):
        raise RegressionError("Regression term names do not match the design")
    if len(y) <= x.shape[1]:
        raise RegressionError("Regression has no residual degrees of freedom")
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        raise RegressionError("Regression input contains a non-finite value")
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise RegressionError("Regression design is exactly rank deficient")
    if max_lags < 0 or max_lags >= len(y):
        raise RegressionError("HAC maximum lag is incompatible with the sample")

    base = sm.OLS(y, x, hasconst=True).fit()
    robust = base.get_robustcov_results(
        cov_type="HAC",
        maxlags=max_lags,
        kernel="bartlett",
        use_correction=True,
        use_t=True,
    )
    interval = np.asarray(robust.conf_int(alpha=0.05), dtype=float)
    cooks = np.asarray(base.get_influence().cooks_distance[0], dtype=float)

    diagnostic_lags = min(max(1, max_lags), max(1, len(y) - x.shape[1] - 1))
    try:
        bg_p_value = float(acorr_breusch_godfrey(base, nlags=diagnostic_lags)[1])
        if not math.isfinite(bg_p_value):
            bg_p_value = None
    except (ValueError, ZeroDivisionError):
        bg_p_value = None
    try:
        adf_p_value = float(adfuller(base.resid, regression="n", autolag="AIC")[1])
        if not math.isfinite(adf_p_value):
            adf_p_value = None
    except (ValueError, ZeroDivisionError):
        adf_p_value = None

    return RegressionFit(
        term_names=names,
        coefficients=_finite_tuple(robust.params, label="coefficients"),
        standard_errors=_finite_tuple(robust.bse, label="standard errors"),
        p_values=_finite_tuple(robust.pvalues, label="p-values"),
        confidence_interval_low=_finite_tuple(interval[:, 0], label="confidence interval"),
        confidence_interval_high=_finite_tuple(interval[:, 1], label="confidence interval"),
        residuals=_finite_tuple(base.resid, label="residuals"),
        fitted_values=_finite_tuple(base.fittedvalues, label="fitted values"),
        residual_degrees_of_freedom=int(base.df_resid),
        condition_number=_standardised_condition_number(x),
        breusch_godfrey_p_value=bg_p_value,
        adf_p_value=adf_p_value,
        cooks_distances=_finite_tuple(cooks, label="Cook's distances"),
        max_lags=max_lags,
    )
