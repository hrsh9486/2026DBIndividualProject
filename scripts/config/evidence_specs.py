"""Versioned, non-executable specifications for the first evidence analyses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from config.focused_indicators import FOCUSED_BUNDLES
from models import EvidenceClass, ObservationStatus


SPECIFICATION_REGISTRY_VERSION = "1.2.0"


class AlignmentStrategy(str, Enum):
    EXACT_DATE_INNER_JOIN = "exact_date_inner_join"
    CALENDAR_YEAR_INNER_JOIN = "calendar_year_inner_join"
    FISCAL_YEAR_END_INNER_JOIN = "fiscal_year_end_inner_join"
    QUARTER_END_INNER_JOIN = "quarter_end_inner_join"
    MONTHLY_TO_QUARTERLY_MEAN = "monthly_to_quarterly_mean"
    MONTHLY_TO_QUARTERLY_END = "monthly_to_quarterly_end"
    MONTHLY_TO_QUARTERLY_SUM = "monthly_to_quarterly_sum"
    LAG_THEN_INNER_JOIN = "lag_then_inner_join"
    EVENT_WINDOW_JOIN = "event_window_join"


class Transformation(str, Enum):
    LEVEL = "level"
    DIFFERENCE = "difference"
    LOG = "log"
    LOG_DIFFERENCE = "log_difference"


class Estimator(str, Enum):
    OLS = "ols"
    LOG_LINEAR_SEGMENTED_TREND = "log_linear_segmented_trend"


class Covariance(str, Enum):
    HAC = "HAC"


class ExpectedDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    TWO_SIDED = "two_sided"


class SupportRule(str, Enum):
    ALL_FOCAL_ADJUSTED_SIGNIFICANT = "all_focal_adjusted_p_below_alpha"


@dataclass(frozen=True, slots=True)
class ExceptionalPeriod:
    key: str
    start_date: date
    end_date: date
    treatment: str


@dataclass(frozen=True, slots=True)
class SeriesInput:
    name: str
    asset_path: str
    series_key: str
    role: str
    expected_unit: str
    expected_frequency: str
    allowed_statuses: tuple[ObservationStatus, ...]
    transformation: Transformation = Transformation.LEVEL
    lag_periods: int = 0


@dataclass(frozen=True, slots=True)
class EvidenceSpec:
    key: str
    version: str
    lens_key: str
    label: str
    claim: str
    null_hypothesis: str
    evidence_class: EvidenceClass
    inputs: tuple[SeriesInput, ...]
    alignment: AlignmentStrategy
    estimator: Estimator
    formula: str
    covariance: Covariance
    covariance_max_lags: int
    minimum_observations: int
    minimum_complete_pairs: int
    fitted_parameter_count: int
    minimum_residual_degrees_of_freedom: int
    diagnostics: tuple[str, ...]
    robustness: tuple[str, ...]
    focal_terms: tuple[str, ...]
    expected_direction: ExpectedDirection
    support_rule: SupportRule
    multiple_testing_family: str
    alpha: float
    causal: bool
    limitation: str
    analysis_start_date: date | None = None
    break_date: date | None = None
    exceptional_periods: tuple[ExceptionalPeriod, ...] = ()


_FISCAL_ASSET = "fiscal-capacity/debt-and-interest-burden.json"
_DIGITAL_ASSET = "digital-integration/upi-and-tax-capacity.json"
_HISTORICAL_STATUSES = (ObservationStatus.ACTUAL, ObservationStatus.REVISED)


EVIDENCE_SPECS: dict[str, EvidenceSpec] = {
    spec.key: spec
    for spec in (
        EvidenceSpec(
            key="debt-interest-burden-change",
            version="1.0.0",
            lens_key="fiscal_capacity",
            label="Lagged debt and change in interest burden",
            claim="Higher lagged general-government debt is associated with a subsequent increase in the central-government interest-to-revenue burden.",
            null_hypothesis="The coefficient on lagged general-government debt is zero.",
            evidence_class=EvidenceClass.ASSOCIATIONAL,
            inputs=(
                SeriesInput(
                    "interest_burden_change", _FISCAL_ASSET, "interest_payments_pct_revenue",
                    "dependent", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    Transformation.DIFFERENCE,
                ),
                SeriesInput(
                    "lagged_general_government_debt", _FISCAL_ASSET, "general_government_debt_pct_gdp",
                    "focal", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    lag_periods=1,
                ),
                SeriesInput(
                    "lagged_primary_balance", _FISCAL_ASSET, "primary_balance_pct_gdp",
                    "control", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    lag_periods=1,
                ),
            ),
            alignment=AlignmentStrategy.LAG_THEN_INNER_JOIN,
            estimator=Estimator.OLS,
            formula="delta_interest_burden ~ lagged_general_government_debt + lagged_primary_balance + trend",
            covariance=Covariance.HAC,
            covariance_max_lags=2,
            minimum_observations=30,
            minimum_complete_pairs=30,
            fitted_parameter_count=4,
            minimum_residual_degrees_of_freedom=20,
            diagnostics=(
                "residual_degrees_of_freedom",
                "condition_number",
                "residual_autocorrelation",
                "stationarity",
                "influential_observation",
            ),
            robustness=(
                "exclude_covid_fiscal_years",
                "actual_status_only",
                "hac_max_lags_1",
                "exclude_most_influential",
                "parsimonious_bivariate",
            ),
            focal_terms=("lagged_general_government_debt",),
            expected_direction=ExpectedDirection.POSITIVE,
            support_rule=SupportRule.ALL_FOCAL_ADJUSTED_SIGNIFICANT,
            multiple_testing_family="fiscal_capacity_primary",
            alpha=0.05,
            causal=False,
            limitation="General-government debt and central-government interest burden have different institutional coverage; the model is associational.",
            exceptional_periods=(
                ExceptionalPeriod(
                    "covid_fiscal_years", date(2020, 4, 1), date(2022, 3, 31),
                    "retain in the main model; exclude in registered robustness",
                ),
            ),
        ),
        EvidenceSpec(
            key="primary-balance-debt-change",
            version="1.2.0",
            lens_key="fiscal_capacity",
            label="Primary balance and subsequent debt movement",
            claim="A stronger lagged primary balance is associated with a subsequent reduction in general-government debt.",
            null_hypothesis="The coefficient on the lagged primary balance is zero.",
            evidence_class=EvidenceClass.ASSOCIATIONAL,
            inputs=(
                SeriesInput(
                    "debt_change", _FISCAL_ASSET, "general_government_debt_pct_gdp",
                    "dependent", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    Transformation.DIFFERENCE,
                ),
                SeriesInput(
                    "lagged_primary_balance", _FISCAL_ASSET, "primary_balance_pct_gdp",
                    "focal", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    lag_periods=1,
                ),
                SeriesInput(
                    "lagged_debt_change", _FISCAL_ASSET, "general_government_debt_pct_gdp",
                    "control", "percent", "fiscal_year", _HISTORICAL_STATUSES,
                    Transformation.DIFFERENCE, lag_periods=1,
                ),
            ),
            alignment=AlignmentStrategy.LAG_THEN_INNER_JOIN,
            estimator=Estimator.OLS,
            formula="debt_change ~ lagged_primary_balance + lagged_debt_change + covid_fy2020_22",
            covariance=Covariance.HAC,
            covariance_max_lags=2,
            minimum_observations=30,
            minimum_complete_pairs=30,
            fitted_parameter_count=4,
            minimum_residual_degrees_of_freedom=20,
            diagnostics=(
                "residual_degrees_of_freedom",
                "condition_number",
                "residual_autocorrelation",
                "stationarity",
                "influential_observation",
            ),
            robustness=(
                "exclude_covid_fiscal_years",
                "actual_status_only",
                "hac_max_lags_1",
                "exclude_most_influential",
                "parsimonious_bivariate",
            ),
            focal_terms=("lagged_primary_balance",),
            expected_direction=ExpectedDirection.NEGATIVE,
            support_rule=SupportRule.ALL_FOCAL_ADJUSTED_SIGNIFICANT,
            multiple_testing_family="fiscal_capacity_primary",
            alpha=0.05,
            causal=False,
            limitation="Debt dynamics also reflect nominal growth, valuation effects and stock-flow adjustments not isolated by this model.",
            exceptional_periods=(
                ExceptionalPeriod(
                    "covid_fiscal_years", date(2020, 4, 1), date(2022, 3, 31),
                    "retain as registered indicators; exclude in registered robustness",
                ),
            ),
        ),
        EvidenceSpec(
            key="upi-adoption-trend",
            version="1.0.0",
            lens_key="digital_integration",
            label="Persistent UPI adoption trend",
            claim="UPI transactions per capita show a persistent adoption trend beyond ordinary calendar-month variation.",
            null_hypothesis="The annualised underlying adoption trend is zero.",
            evidence_class=EvidenceClass.ASSOCIATIONAL,
            inputs=(
                SeriesInput(
                    "log_upi_transactions_per_capita", _DIGITAL_ASSET, "upi_transactions_per_capita",
                    "dependent", "transactions_per_person", "monthly",
                    (ObservationStatus.ACTUAL,), Transformation.LOG,
                ),
            ),
            alignment=AlignmentStrategy.EXACT_DATE_INNER_JOIN,
            estimator=Estimator.LOG_LINEAR_SEGMENTED_TREND,
            formula="log_upi_transactions_per_capita ~ trend + calendar_month_effects + covid_level + post_covid_slope",
            covariance=Covariance.HAC,
            covariance_max_lags=12,
            minimum_observations=36,
            minimum_complete_pairs=36,
            fitted_parameter_count=15,
            minimum_residual_degrees_of_freedom=20,
            diagnostics=(
                "residual_degrees_of_freedom",
                "condition_number",
                "residual_autocorrelation",
                "influential_observation",
                "stability",
            ),
            robustness=(
                "start_date_2018_04",
                "exclude_pandemic_disruption_months",
                "linear_level_trend",
                "hac_max_lags_6",
            ),
            focal_terms=("annualised_underlying_trend",),
            expected_direction=ExpectedDirection.POSITIVE,
            support_rule=SupportRule.ALL_FOCAL_ADJUSTED_SIGNIFICANT,
            multiple_testing_family="digital_integration_primary",
            alpha=0.05,
            causal=False,
            limitation="The trend measures network adoption over time; it does not identify a policy effect or a causal effect on formalisation.",
            analysis_start_date=date(2017, 4, 30),
            break_date=date(2020, 4, 30),
            exceptional_periods=(
                ExceptionalPeriod(
                    "pandemic_disruption", date(2020, 3, 31), date(2020, 6, 30),
                    "retain with registered level and slope terms; exclude in robustness",
                ),
            ),
        ),
    )
}


EVIDENCE_OUTPUT_PATHS = {
    lens_key: f"evidence/{lens_key.replace('_', '-')}.json"
    for lens_key in FOCUSED_BUNDLES
}


def evidence_specs_for_lens(lens_key: str) -> tuple[EvidenceSpec, ...]:
    return tuple(spec for spec in EVIDENCE_SPECS.values() if spec.lens_key == lens_key)


def validate_evidence_specs() -> None:
    if len(EVIDENCE_SPECS) != len({spec.key for spec in EVIDENCE_SPECS.values()}):
        raise ValueError("Evidence analysis keys must be unique")
    focused_paths = {
        bundle.output_path: bundle
        for bundle in FOCUSED_BUNDLES.values()
    }
    for spec in EVIDENCE_SPECS.values():
        if spec.lens_key not in FOCUSED_BUNDLES:
            raise ValueError(f"Unknown evidence lens: {spec.lens_key}")
        if not 0 < spec.alpha < 1:
            raise ValueError(f"Evidence alpha must be inside (0, 1): {spec.key}")
        if spec.minimum_observations <= 0 or spec.minimum_complete_pairs <= 0:
            raise ValueError(f"Evidence sample thresholds must be positive: {spec.key}")
        if spec.causal:
            raise ValueError(f"Causal specifications require a separate identification design: {spec.key}")
        if not spec.multiple_testing_family:
            raise ValueError(f"Inferential specification lacks a testing family: {spec.key}")
        if not spec.focal_terms or len(spec.focal_terms) != len(set(spec.focal_terms)):
            raise ValueError(f"Evidence focal terms must be non-empty and unique: {spec.key}")
        names = [item.name for item in spec.inputs]
        if len(names) != len(set(names)):
            raise ValueError(f"Evidence input names must be unique: {spec.key}")
        if not any(item.role == "dependent" for item in spec.inputs):
            raise ValueError(f"Evidence specification has no dependent input: {spec.key}")
        if not any(item.role == "focal" for item in spec.inputs) and len(spec.inputs) > 1:
            raise ValueError(f"Evidence specification has no focal input: {spec.key}")
        for item in spec.inputs:
            bundle = focused_paths.get(item.asset_path)
            if bundle is None:
                raise ValueError(f"Unregistered focused artifact: {item.asset_path}")
            series = next((candidate for candidate in bundle.series if candidate.key == item.series_key), None)
            if series is None:
                raise ValueError(f"Unknown series {item.series_key} in {item.asset_path}")
            if series.unit != item.expected_unit or series.frequency != item.expected_frequency:
                raise ValueError(
                    f"Evidence input contract drift for {spec.key}/{item.name}: "
                    f"expected {series.unit}/{series.frequency}, declared "
                    f"{item.expected_unit}/{item.expected_frequency}"
                )
            if item.lag_periods < 0:
                raise ValueError(f"Evidence lags cannot be negative: {spec.key}/{item.name}")


validate_evidence_specs()
