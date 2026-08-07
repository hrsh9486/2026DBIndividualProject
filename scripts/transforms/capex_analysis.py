"""Deterministic transformations for the public-CapEx transmission analysis."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config.capex_analysis import (
    BENCHMARK_KEY,
    CONTROL_KEY,
    CONTROL_RELATIVE_KEYS,
    MARKET_LAGS_MONTHS,
    TARGET_KEYS,
)
from helper import clean_float
from models import CanonicalRecord
from models.capex_metrics import FiscalMetrics, GovernmentMetrics, PrivateMetrics


def _maximum_drawdown(wealth: pd.Series) -> float | None:
    if wealth.empty:
        return None
    return clean_float((wealth / wealth.cummax() - 1).min())


def build_sector_performance_payload(
    prices: pd.DataFrame,
    definitions: dict[str, dict[str, str]],
    *,
    benchmark_key: str = BENCHMARK_KEY,
    source: str = "NSE Indices historical total-return index",
) -> dict:
    """Build monthly total/excess-return histories on one common period."""
    required = [
        benchmark_key,
        *[key for key in TARGET_KEYS if key in definitions],
        *([CONTROL_KEY] if CONTROL_KEY in definitions else []),
    ]
    missing = [key for key in required if key not in prices or prices[key].dropna().empty]
    if missing:
        raise ValueError(f"Missing required market histories: {', '.join(missing)}")
    common = prices[required].sort_index().dropna()
    periods = common.index.to_period("M")
    monthly = common.groupby(periods).last()
    monthly.index = pd.DatetimeIndex(
        [common.index[periods == period].max() for period in monthly.index]
    )
    if len(monthly) < 13:
        raise ValueError("Sector analysis requires at least 13 common monthly observations")
    returns = monthly.pct_change(fill_method=None)
    benchmark = returns[benchmark_key]
    markets: dict[str, dict] = {}
    for key in required:
        total_return = returns[key]
        excess_return = total_return - benchmark
        relative_wealth = ((1 + total_return) / (1 + benchmark)).cumprod() * 100
        normalized_total = monthly[key] / monthly[key].iloc[0] * 100
        if key == benchmark_key:
            relative_wealth[:] = 100.0
            excess_return[:] = 0.0
        rolling_excess = excess_return.rolling(12).sum()
        rolling_volatility = excess_return.rolling(12).std() * math.sqrt(12)
        observations = []
        for date, price in monthly[key].items():
            observations.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": clean_float(price),
                "normalized_value": clean_float(normalized_total.get(date)),
                "relative_to_nifty50": clean_float(relative_wealth.get(date)),
                "return": clean_float(excess_return.get(date)),
                "raw_return": clean_float(total_return.get(date)),
                "drawdown": clean_float(relative_wealth.get(date) / relative_wealth.loc[:date].max() - 1),
                "rolling_volatility": clean_float(rolling_volatility.get(date)),
                "rolling_12m_excess_return": clean_float(rolling_excess.get(date)),
            })
        valid_returns = total_return.dropna()
        years = max(len(valid_returns) / 12, 1 / 12)
        markets[key] = {
            "label": definitions[key]["label"],
            "ticker": definitions[key]["ticker"],
            "currency": "INR",
            "summary": {
                "total_return": clean_float(monthly[key].iloc[-1] / monthly[key].iloc[0] - 1),
                "cagr": clean_float((monthly[key].iloc[-1] / monthly[key].iloc[0]) ** (1 / years) - 1),
                "annualized_volatility": clean_float(valid_returns.std() * math.sqrt(12)),
                "sharpe_ratio": clean_float(valid_returns.mean() / valid_returns.std() * math.sqrt(12)) if valid_returns.std() else None,
                "max_drawdown": _maximum_drawdown(monthly[key]),
                "excess_total_return": clean_float(relative_wealth.iloc[-1] / 100 - 1),
                "excess_max_drawdown": _maximum_drawdown(relative_wealth),
            },
            "series": observations,
        }
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "start_date": monthly.index.min().strftime("%Y-%m-%d"),
            "end_date": monthly.index.max().strftime("%Y-%m-%d"),
            "base_value": 100,
            "risk_free_rate": 0,
            "interval": "monthly",
            "benchmark": benchmark_key,
            "note": "Normalized values rebase each standalone TRI to 100 at the common start date. The separate relative_to_nifty50 field retains compounded sector performance versus the Nifty 50.",
        },
        "markets": markets,
        "correlations": [],
    }


def _record_series(records: tuple[CanonicalRecord, ...], indicator: str) -> pd.Series:
    series = pd.Series(
        {
            pd.Timestamp(record.date): record.value
            for record in records
            if record.indicator == indicator and record.value is not None
        },
        dtype=float,
    ).sort_index()
    return series


def capex_growth_series(government: GovernmentMetrics) -> pd.Series:
    series = _record_series(government.records, "capex_actual")
    return series.pct_change(fill_method=None) * 100


def sector_monthly_return(sector_payload: dict, key: str, *, raw: bool = False) -> pd.Series:
    if key in CONTROL_RELATIVE_KEYS:
        target_key = key.removesuffix("_VS_FMCG")
        target = sector_monthly_return(sector_payload, target_key, raw=True)
        control = sector_monthly_return(sector_payload, CONTROL_KEY, raw=True)
        aligned = pd.concat([target.rename("target"), control.rename("control")], axis=1).dropna()
        return aligned["target"] - aligned["control"]
    field = "raw_return" if raw else "return"
    return pd.Series(
        {
            pd.Timestamp(row["date"]): row.get(field)
            for row in sector_payload["markets"][key]["series"]
            if row.get(field) is not None
        },
        dtype=float,
    ).sort_index()


def build_lag_analysis(
    government: GovernmentMetrics,
    sector_payload: dict,
    private: PrivateMetrics | None = None,
) -> tuple[dict, dict]:
    """Relate fiscal-year CapEx growth to subsequent sector excess returns."""
    capex = capex_growth_series(government)
    capex_values = [
        {
            "date": date_value.strftime("%Y-%m-%d"),
            "period_label": f"FY{date_value.year - 1}-{str(date_value.year)[-2:]}",
            "value": clean_float(value),
            "status": "actual",
        }
        for date_value, value in capex.dropna().items()
    ]
    series: dict[str, dict] = {
        "nominal_capex_growth": {
            "label": "Actual nominal CapEx growth",
            "entity": "IND",
            "unit": "percent",
            "is_derived": True,
            "methodology": "Year-on-year change in actual central-government capital expenditure.",
            "source_note": "Nominal growth includes inflation and does not measure project quality.",
            "values": capex_values,
        }
    }
    estimates: dict[str, dict[str, float | int | None]] = {}
    for key in (*TARGET_KEYS, BENCHMARK_KEY, *CONTROL_RELATIVE_KEYS):
        is_benchmark = key == BENCHMARK_KEY
        excess = sector_monthly_return(sector_payload, key, raw=is_benchmark)
        if excess.empty:
            continue
        label = (
            f"{sector_payload['markets'][key.removesuffix('_VS_FMCG')]['label']} vs Nifty FMCG"
            if key in CONTROL_RELATIVE_KEYS
            else sector_payload["markets"][key]["label"]
        )
        for lag in MARKET_LAGS_MONTHS:
            values = []
            pairs = []
            for fiscal_end, growth in capex.dropna().items():
                window_start = fiscal_end + pd.offsets.MonthEnd(lag)
                window_end = window_start + pd.offsets.MonthEnd(12)
                subsequent = excess[(excess.index > window_start) & (excess.index <= window_end)]
                if len(subsequent) < 9:
                    continue
                sector_return = ((1 + subsequent).prod() - 1) * 100
                values.append({
                    "date": fiscal_end.strftime("%Y-%m-%d"),
                    "period_label": f"FY{fiscal_end.year - 1}-{str(fiscal_end.year)[-2:]}",
                    "value": clean_float(sector_return),
                    "status": "actual",
                })
                pairs.append((float(growth), float(sector_return), fiscal_end.year))
            series_key = f"{key.lower()}_lag_{lag}m"
            series[series_key] = {
                    "label": f"{label}: subsequent 12-month {'market' if is_benchmark else 'excess'} return ({lag}-month lag)",
                "entity": "IND",
                "unit": "percent",
                "is_derived": True,
                "methodology": (
                    "Compound monthly broad-market returns over the subsequent 12 months."
                    if is_benchmark
                    else "Compound monthly sector-minus-benchmark returns over the subsequent 12 months."
                ),
                "source_note": "Small annual samples are descriptive and do not establish causality.",
                "values": values,
            }
            frame = pd.DataFrame(pairs, columns=["capex", "sector", "fiscal_end_year"])
            sensitivity = frame[~frame["fiscal_end_year"].isin((2021, 2022))]
            estimates[series_key] = {
                "label": label,
                "lag": lag,
                "lag_unit": "months",
                "outcome_type": "market",
                "direction": "capex_leads",
                "pearson": clean_float(frame.corr(method="pearson").iloc[0, 1]) if len(frame) >= 3 else None,
                "spearman": clean_float(frame.corr(method="spearman").iloc[0, 1]) if len(frame) >= 3 else None,
                "n": len(frame),
                "pearson_excluding_pandemic": clean_float(sensitivity[["capex", "sector"]].corr(method="pearson").iloc[0, 1]) if len(sensitivity) >= 3 else None,
                "n_excluding_pandemic": len(sensitivity),
            }
        for lead in (3, 6, 12):
            values = []
            pairs = []
            for fiscal_end, growth in capex.dropna().items():
                window_end = fiscal_end - pd.offsets.MonthEnd(lead)
                window_start = window_end - pd.offsets.MonthEnd(12)
                preceding = excess[(excess.index > window_start) & (excess.index <= window_end)]
                if len(preceding) < 9:
                    continue
                market_return = ((1 + preceding).prod() - 1) * 100
                values.append({
                    "date": fiscal_end.strftime("%Y-%m-%d"),
                    "period_label": f"FY{fiscal_end.year - 1}-{str(fiscal_end.year)[-2:]}",
                    "value": clean_float(market_return),
                    "status": "actual",
                })
                pairs.append((float(growth), float(market_return), fiscal_end.year))
            series_key = f"{key.lower()}_lead_{lead}m"
            series[series_key] = {
                "label": f"{label}: 12-month {'market' if is_benchmark else 'excess'} return ending {lead} months before CapEx",
                "entity": "IND",
                "unit": "percent",
                "is_derived": True,
                "methodology": f"Compound monthly return over the 12-month window ending {lead} months before the fiscal-year CapEx observation.",
                "source_note": "This tests market anticipation, not whether later expenditure caused the preceding return.",
                "values": values,
            }
            frame = pd.DataFrame(pairs, columns=["capex", "sector", "fiscal_end_year"])
            sensitivity = frame[~frame["fiscal_end_year"].isin((2021, 2022))]
            estimates[series_key] = {
                "label": label,
                "lag": lead,
                "lag_unit": "months",
                "outcome_type": "market",
                "direction": "market_leads",
                "pearson": clean_float(frame.corr(method="pearson").iloc[0, 1]) if len(frame) >= 3 else None,
                "spearman": clean_float(frame.corr(method="spearman").iloc[0, 1]) if len(frame) >= 3 else None,
                "n": len(frame),
                "pearson_excluding_pandemic": clean_float(sensitivity[["capex", "sector"]].corr(method="pearson").iloc[0, 1]) if len(sensitivity) >= 3 else None,
                "n_excluding_pandemic": len(sensitivity),
            }
    if private is not None:
        gfcf_series = _record_series(
            private.records,
            "private_corporate_gfcf_pct_gdp",
        )
        gfcf = {date_value: float(value) for date_value, value in gfcf_series.items()}
        for lag in (0, 1, 2):
            values = []
            pairs = []
            for fiscal_end, growth in capex.dropna().items():
                outcome_date = fiscal_end + pd.DateOffset(years=lag)
                outcome = gfcf.get(outcome_date)
                if outcome is None:
                    continue
                values.append({
                    "date": fiscal_end.strftime("%Y-%m-%d"),
                    "period_label": f"FY{fiscal_end.year - 1}-{str(fiscal_end.year)[-2:]}",
                    "value": clean_float(outcome),
                    "status": "actual",
                })
                pairs.append((float(growth), outcome, fiscal_end.year))
            series_key = f"private_gfcf_lag_{lag}y"
            series[series_key] = {
                "label": f"Private corporate GFCF/GDP ({lag}-year lag)",
                "entity": "IND",
                "unit": "percent",
                "is_derived": lag > 0,
                "methodology": "Private corporate GFCF/GDP aligned to the CapEx fiscal year at a fixed annual lag.",
                "source_note": "The consistent national-accounts history is too short for a reliable correlation estimate.",
                "values": values,
            }
            frame = pd.DataFrame(pairs, columns=["capex", "outcome", "fiscal_end_year"])
            estimates[series_key] = {
                "label": "Private corporate GFCF/GDP",
                "lag": lag,
                "lag_unit": "years",
                "outcome_type": "real_economy",
                "direction": "capex_leads",
                "pearson": clean_float(frame[["capex", "outcome"]].corr(method="pearson").iloc[0, 1]) if len(frame) >= 3 else None,
                "spearman": clean_float(frame[["capex", "outcome"]].corr(method="spearman").iloc[0, 1]) if len(frame) >= 3 else None,
                "n": len(frame),
                "pearson_excluding_pandemic": None,
                "n_excluding_pandemic": len(frame[~frame["fiscal_end_year"].isin((2021, 2022))]),
            }
    all_dates = [
        row["date"] for item in series.values() for row in item["values"]
    ]
    if not all_dates:
        raise ValueError("No aligned CapEx/sector observations")
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [
                {"name": "Validated central-government CapEx artifact"},
                {"name": "Validated CapEx-sector market artifact"},
            ],
            "frequency": "annual",
            "start_date": min(all_dates),
            "end_date": max(all_dates),
            "indicator_code": "CAPEX_SECTOR_LAG_ANALYSIS",
            "label": "CapEx growth and subsequent sector performance",
            "default_unit": "percent",
            "series_order": list(series),
            "is_derived": True,
            "methodology": "Fiscal-year nominal CapEx growth is paired with subsequent market returns at 0, 6 and 12 months; preceding market returns ending 3, 6 and 12 months before CapEx; and private corporate GFCF/GDP at 0, 1 and 2 fiscal years.",
            "correlation_estimates": estimates,
            "note": "Associational timing test only. Markets may anticipate budgets and the annual sample is small.",
        },
        "series": series,
    }
    return payload, estimates


def classify_summary(
    government: GovernmentMetrics,
    private: PrivateMetrics,
    fiscal: FiscalMetrics,
    correlation_estimates: dict,
) -> dict:
    """Create reproducible, conservative hypothesis classifications."""
    capex_gdp = list(_record_series(government.records, "actual_capex_pct_gdp"))
    capex_share = list(_record_series(
        government.records,
        "actual_capex_pct_total_expenditure",
    ))
    h1_supported = len(capex_gdp) >= 2 and len(capex_share) >= 2 and capex_gdp[-1] > capex_gdp[0] and capex_share[-1] > capex_share[0]
    usable_corr = [
        item["pearson"]
        for item in correlation_estimates.values()
        if item["pearson"] is not None
        and item["n"] >= 4
        and item.get("direction", "capex_leads") == "capex_leads"
        and item.get("outcome_type") == "market"
        and item.get("label") != "Nifty 50"
    ]
    h2 = "supported" if usable_corr and sum(value > 0 for value in usable_corr) / len(usable_corr) >= 2 / 3 else ("partially_supported" if any(value > 0 for value in usable_corr) else "inconclusive")
    private_gfcf = list(_record_series(
        private.records,
        "private_corporate_gfcf_pct_gdp",
    ))
    capacity = list(_record_series(
        private.records,
        "manufacturing_capacity_utilisation",
    ))
    if len(private_gfcf) < 4 or len(capacity) < 4:
        h3 = "inconclusive"
    else:
        h3 = "supported" if private_gfcf[-1] > private_gfcf[0] and capacity[-1] > capacity[0] else "partially_supported"
    debt = list(_record_series(fiscal.records, "general_government_debt_pct_gdp"))
    interest = list(_record_series(fiscal.records, "interest_payments_pct_revenue"))
    h4 = "partially_supported" if debt and interest else "inconclusive"
    hypotheses = [
        ("capex_intensity", "Actual public CapEx increased relative to GDP and expenditure.", "supported" if h1_supported else "unsupported"),
        ("sector_transmission", "Higher CapEx growth preceded excess returns in CapEx-sensitive sectors.", h2),
        ("real_economy_conversion", "Private investment and capacity increased after the CapEx push.", h3),
        ("fiscal_sustainability", "Debt service has not clearly made the strategy unsustainable.", h4),
    ]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "research_question": "Did India's public CapEx push transmit into sectoral and real economic growth strongly enough to justify its fiscal cost?",
            "classification_method": "Deterministic rules recorded in scripts/transforms/capex_analysis.py; classifications are evidence summaries, not causal estimates.",
        },
        "hypotheses": [
            {
                "key": key,
                "hypothesis": hypothesis,
                "status": status,
                "interpretation": {
                    "supported": "Available indicators move in the hypothesised direction.",
                    "partially_supported": "Some indicators are consistent with the hypothesis, but the evidence is mixed or incomplete.",
                    "unsupported": "Available indicators do not move in the hypothesised direction.",
                    "inconclusive": "The aligned history is too short for a defensible classification.",
                }[status],
                "caveat": "Descriptive and associational evidence cannot by itself identify the causal effect of public CapEx.",
            }
            for key, hypothesis, status in hypotheses
        ],
    }
