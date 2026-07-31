"""Frozen definitions for the India public-CapEx transmission project."""

from __future__ import annotations

from dataclasses import dataclass


ANALYSIS_START = "2018-04-01"
PANDEMIC_FISCAL_YEARS = frozenset({2020, 2021})
MARKET_LAGS_MONTHS = (0, 6, 12)
STRUCTURAL_LAGS_YEARS = (0, 1, 2)
ROLLING_CORRELATION_MONTHS = 36


@dataclass(frozen=True, slots=True)
class CapexMarket:
    key: str
    label: str
    ticker: str
    role: str


# Yahoo symbols are an automated fallback. The artifact labels the provider and
# preserves raw observations; an official Nifty history can be supplied to the
# pure build functions without changing the analysis.
CAPEX_MARKETS = (
    CapexMarket("CAPITAL_GOODS", "Nifty Capital Goods", "NIFTY CAPITAL GOODS", "target"),
    CapexMarket("INFRASTRUCTURE", "Nifty Infrastructure", "NIFTY INFRASTRUCTURE", "target"),
    CapexMarket("MANUFACTURING", "Nifty India Manufacturing", "NIFTY INDIA MANUFACTURING", "target"),
    CapexMarket("NIFTY_50", "Nifty 50", "NIFTY 50", "benchmark"),
    CapexMarket("FMCG", "Nifty FMCG", "NIFTY FMCG", "control"),
)

BENCHMARK_KEY = "NIFTY_50"
TARGET_KEYS = tuple(market.key for market in CAPEX_MARKETS if market.role == "target")
CONTROL_KEY = "FMCG"
CONTROL_RELATIVE_KEYS = tuple(f"{key}_VS_FMCG" for key in TARGET_KEYS)


@dataclass(frozen=True, slots=True)
class CorporateCase:
    key: str
    label: str
    ticker: str
    group: str


# Frozen before the corporate results are examined. The basket favours large,
# liquid firms with a clear capital-goods or infrastructure operating exposure.
CORPORATE_CASES = (
    CorporateCase("LT", "Larsen & Toubro", "LT.NS", "capital_goods"),
    CorporateCase("SIEMENS", "Siemens India", "SIEMENS.NS", "capital_goods"),
    CorporateCase("ABB", "ABB India", "ABB.NS", "capital_goods"),
    CorporateCase("BEL", "Bharat Electronics", "BEL.NS", "capital_goods"),
    CorporateCase("CUMMINS", "Cummins India", "CUMMINSIND.NS", "capital_goods"),
    CorporateCase("NTPC", "NTPC", "NTPC.NS", "infrastructure"),
    CorporateCase("POWERGRID", "Power Grid Corporation", "POWERGRID.NS", "infrastructure"),
    CorporateCase("ADANIPORTS", "Adani Ports", "ADANIPORTS.NS", "infrastructure"),
    CorporateCase("ULTRACEMCO", "UltraTech Cement", "ULTRACEMCO.NS", "infrastructure"),
    CorporateCase("IRCTC", "IRCTC", "IRCTC.NS", "infrastructure"),
)

OUTPUTS = {
    "execution": "capex-analysis/capex-execution.json",
    "allocation": "capex-analysis/sector-capex-allocation.json",
    "delivery": "capex-analysis/physical-delivery.json",
    "production": "capex-analysis/capital-goods-production.json",
    "sectors": "capex-analysis/sector-performance.json",
    "correlations": "capex-analysis/capex-sector-correlations.json",
    "private": "capex-analysis/private-investment-response.json",
    "fiscal": "capex-analysis/fiscal-sustainability.json",
    "summary": "capex-analysis/analysis-summary.json",
    "corporate": "capex-analysis/corporate-fundamentals.json",
}
