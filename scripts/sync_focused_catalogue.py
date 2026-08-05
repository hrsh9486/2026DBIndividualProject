"""Build the static frontend catalogue for the CapEx transmission product."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import PROJECT_ROOT
from config.capex_analysis import OUTPUTS as CAPEX_OUTPUTS
from exporters import write_json_atomic
from validators import validate_payload


CATALOGUE_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "catalogue.json"
FRONTEND_SCHEMA_DIR = PROJECT_ROOT / "frontend" / "public" / "data" / "schemas"


def _stale_after_days(frequency: str) -> int:
    return {"monthly": 45, "annual": 450, "mixed": 120}.get(frequency, 120)


def build_catalogue(catalogue: dict, *, public_data_dir: Path) -> dict:
    """Return a catalogue containing only the active CapEx story."""
    catalogue = {
        "schema_version": catalogue.get("schema_version", "1.0.0"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "public_data_root": catalogue.get("public_data_root", "/data"),
        "assets": {},
        "sections": [],
    }

    capex_asset_specs = {
        "capex-execution": ("execution", "dated_multi_series", "annual", "Has actual public CapEx intensified and been executed?"),
        "capex-sector-allocation": ("allocation", "dated_multi_series", "annual", "How much central-budget CapEx was allocated to roads and railways?"),
        "capex-physical-delivery": ("delivery", "dated_multi_series", "annual", "Did roads and railways deliver physical output?"),
        "capex-capital-goods-production": ("production", "dated_multi_series", "annual", "Did capital-goods production rise alongside the CapEx push?"),
        "capex-sector-performance": ("sectors", "market_performance", "monthly", "Did CapEx-sensitive sectors outperform the Nifty 50?"),
        "capex-sector-correlations": ("correlations", "dated_multi_series", "annual", "Was CapEx growth followed by sector excess returns?"),
        "capex-private-response": ("private", "dated_multi_series", "mixed", "Did private investment and manufacturing capacity respond?"),
        "capex-fiscal-sustainability": ("fiscal", "dated_multi_series", "annual", "Can the CapEx push continue without excessive debt-service pressure?"),
        "capex-corporate-fundamentals": ("corporate", "dated_multi_series", "annual", "Did market expectations coincide with stronger corporate revenue, investment and productive assets?"),
        "capex-investment-quality": ("quality", "dated_multi_series", "annual", "Did monitored central-sector projects improve on delivery timing and cost control?"),
        "capex-state-evaluation": ("states", "dated_multi_series", "annual", "Do within-state changes in capital outlay precede stronger real GSDP growth?"),
        "capex-crowding-in-evidence": ("crowding_in", "dated_multi_series", "annual", "Do private-investment and production outcomes respond at registered CapEx leads?"),
    }
    for asset_id, (output_key, schema, frequency, description) in capex_asset_specs.items():
        path = public_data_dir / CAPEX_OUTPUTS[output_key]
        catalogue["assets"][asset_id] = {
            "data_path": f"/data/{CAPEX_OUTPUTS[output_key]}",
            "schema_path": f"/data/schemas/{schema}.schema.json",
            "schema": schema,
            "expected_frequency": frequency,
            "stale_after_days": _stale_after_days(frequency),
            "cache_strategy": "revalidate",
            "version": datetime.now(timezone.utc).date().isoformat(),
            "availability": "active" if path.is_file() else "planned",
            "description": description,
        }

    capex_section = {
        "id": "capex-transmission",
        "label": "India's public CapEx transmission",
        "order": 1,
        "indicators": [
            {
                "id": "capex-policy-input",
                "title": "1. Public CapEx intensity and execution",
                "summary": "Has central-government capital expenditure increased relative to GDP and total spending, and were original budgets delivered?",
                "default_view": "intensity",
                "views": [
                    _capex_view("intensity", "CapEx intensity", "capex-execution", ["actual_capex_pct_gdp", "actual_capex_pct_total_expenditure"], "percent"),
                    _capex_view("execution", "Execution", "capex-execution", ["capex_execution_ratio"], "percent"),
                    _capex_view("vintages", "BE, RE and actual", "capex-execution", ["capex_budget_estimate", "capex_revised_estimate", "capex_actual"], "crore"),
                ],
            },
            {
                "id": "capex-market-transmission",
                "title": "2A. CapEx-sensitive sector response",
                "summary": "Relative-wealth indices show the compounded performance of each target sector against the Nifty 50.",
                "default_view": "relative",
                "views": [{
                    "id": "relative", "label": "Relative performance", "asset_id": "capex-sector-performance",
                    "presentation": {
                        "component": "market-performance", "chart_type": "line", "x_axis": "date",
                        "market_field": "relative_to_nifty50",
                        "default_visible": ["NIFTY_50", "CAPITAL_GOODS", "INFRASTRUCTURE", "MANUFACTURING", "FMCG"],
                        "value_format": {"style": "index", "scale": 1, "decimals": 1},
                        "controls": {"date_range": True, "entity_toggle": False, "series_toggle": True},
                        "zero_line": False, "show_points": False, "show_source": True, "show_methodology": True,
                    },
                    "note": "Index provider data are preferred; the automated pipeline uses provider-labelled adjusted-close histories and preserves raw observations.",
                }],
            },
            {
                "id": "capex-sector-delivery",
                "title": "1B. Sector allocation and physical delivery",
                "summary": "Separating budget inputs from completed kilometres shows whether the CapEx push moved beyond headline allocations.",
                "default_view": "allocation",
                "views": [
                    _capex_view("allocation", "Central budget allocation", "capex-sector-allocation", ["railways_budget_capex", "roads_budget_capex"], "crore", series_toggle=True),
                    _capex_view("delivery", "Physical delivery", "capex-physical-delivery", ["national_highways_constructed_km", "railway_route_km_electrified"], "number", series_toggle=True),
                ],
            },
            {
                "id": "capex-investment-quality",
                "title": "1C. Investment quality and project delivery",
                "summary": "Project counts, delays and cost overruns test whether higher financial inputs translated into timely, cost-controlled central-sector assets.",
                "default_view": "quality",
                "views": [{
                    "id": "quality",
                    "label": "Project-quality explorer",
                    "asset_id": "capex-investment-quality",
                    "presentation": {
                        "component": "investment-quality",
                        "chart_type": "scatter",
                        "x_axis": "date",
                        "default_visible": ["delayed_share", "on_schedule_share", "cost_overrun_pct"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": False, "show_source": True, "show_methodology": True,
                    },
                    "note": "The 2011 threshold and delay-definition break is shown explicitly. These monitored-project measures assess implementation quality, not social returns.",
                }],
            },
            {
                "id": "capex-corporate-case-study",
                "title": "2C. Corporate fundamentals case study",
                "summary": "A frozen ten-company basket tests whether sector optimism coincided with revenue, earnings, company investment and productive-asset growth.",
                "default_view": "fundamentals",
                "views": [{
                    "id": "fundamentals",
                    "label": "Group fundamentals",
                    "asset_id": "capex-corporate-fundamentals",
                    "presentation": {
                        "component": "corporate-fundamentals",
                        "chart_type": "bar",
                        "x_axis": "date",
                        "default_visible": ["capital_goods_revenue_growth", "infrastructure_revenue_growth"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": True,
                        "show_source": True,
                        "show_methodology": True,
                    },
                    "note": "Unweighted group medians; the basket is a case study rather than a reconstruction of the index. Order books are excluded because consistent histories are not machine-readable.",
                }],
            },
            {
                "id": "capex-lag-test",
                "title": "2B. CapEx growth and market timing",
                "summary": "Explore correlations using a lag heatmap and fiscal-year scatter plot rather than a time-series line.",
                "default_view": "lag",
                "views": [{
                    "id": "lag",
                    "label": "Correlation explorer",
                    "asset_id": "capex-sector-correlations",
                    "presentation": {
                        "component": "capex-correlation",
                        "chart_type": "scatter",
                        "x_axis": "date",
                        "default_visible": ["capital_goods_lag_0m"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": False,
                        "show_source": True,
                        "show_methodology": True,
                    },
                    "note": "Cells with fewer than four aligned observations are marked insufficient; correlation does not establish causality.",
                }],
            },
            {
                "id": "capex-real-conversion",
                "title": "2D. Private investment and capacity conversion",
                "summary": "Private corporate GFCF and capacity utilisation distinguish market re-rating from realised productive investment.",
                "default_view": "investment",
                "views": [
                    _capex_view("investment", "Investment and capacity", "capex-private-response", ["private_corporate_gfcf_pct_gdp", "manufacturing_capacity_utilisation", "public_capex_lagged"], "percent", series_toggle=True),
                    _capex_view("production", "Capital-goods production", "capex-capital-goods-production", ["capital_goods_iip"], "index"),
                ],
            },
            {
                "id": "capex-crowding-in-depth",
                "title": "2E. Crowding-in evidence ladder",
                "summary": "A registered zero- to three-year lag grid triangulates private GFCF, its share of investment, capacity use and capital-goods production—and refuses inference when the sample is too short.",
                "default_view": "lags",
                "views": [{
                    "id": "lags",
                    "label": "Distributed-lag explorer",
                    "asset_id": "capex-crowding-in-evidence",
                    "presentation": {
                        "component": "crowding-in", "chart_type": "scatter", "x_axis": "date",
                        "default_visible": ["nominal_capex_growth"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": True, "show_source": True, "show_methodology": True,
                    },
                    "note": "Every coefficient remains descriptive until it clears the pre-registered eight-observation gate; passing that gate would still establish association, not causation.",
                }],
            },
            {
                "id": "capex-state-evaluation",
                "title": "2F. State capital-outlay evaluation",
                "summary": "A multi-state panel compares actual capital outlay/GSDP with subsequent real GSDP growth and reports a two-way fixed-effects association with state-clustered uncertainty.",
                "default_view": "panel",
                "views": [{
                    "id": "panel",
                    "label": "State panel explorer",
                    "asset_id": "capex-state-evaluation",
                    "presentation": {
                        "component": "state-capex-evaluation", "chart_type": "scatter", "x_axis": "date",
                        "default_visible": ["median_state_capex_pct_gsdp", "median_next_year_real_gsdp_growth"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": True, "show_source": True, "show_methodology": True,
                    },
                    "note": "State and year fixed effects improve comparability but do not remove time-varying confounding or reverse causality; the result is associational, not a causal state multiplier.",
                }],
            },
            {
                "id": "capex-fiscal-constraint",
                "title": "3. Fiscal sustainability",
                "summary": "Compare the evidence of CapEx transmission with the debt-service pressure that constrains future productive spending.",
                "default_view": "bridge",
                "views": [{
                    "id": "bridge",
                    "label": "Transmission versus fiscal cost",
                    "asset_id": "capex-fiscal-sustainability",
                    "presentation": {
                        "component": "fiscal-bridge",
                        "chart_type": "scatter",
                        "x_axis": "date",
                        "default_visible": ["actual_capex_pct_expenditure", "interest_payments_pct_expenditure"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": False,
                        "show_source": True,
                        "show_methodology": True,
                    },
                    "note": "The allocation ratio compares spending shares; it is not a benefit-cost ratio or a causal estimate of returns to public investment.",
                }, _capex_view("burden", "Debt and interest trends", "capex-fiscal-sustainability", ["general_government_debt_pct_gdp", "interest_payments_pct_revenue", "primary_balance_pct_gdp"], "percent", series_toggle=True, zero_line=True)],
            },
            {
                "id": "capex-scenario-lab",
                "title": "4. CapEx transmission scenario lab",
                "summary": "Stress-test a sustained CapEx increase against dynamic debt arithmetic, parameter uncertainty, sensitivity, a break-even frontier and historical one-step errors.",
                "default_view": "model",
                "views": [{
                    "id": "model",
                    "label": "Five-year scenario",
                    "asset_id": "capex-fiscal-sustainability",
                    "presentation": {
                        "component": "capex-scenario-lab",
                        "chart_type": "line",
                        "x_axis": "date",
                        "default_visible": ["general_government_debt_pct_gdp"],
                        "value_format": {"style": "percent", "scale": 1, "decimals": 1},
                        "controls": {"date_range": False, "entity_toggle": False, "series_toggle": False},
                        "zero_line": False,
                        "show_source": True,
                        "show_methodology": True,
                    },
                    "note": "The latest non-budget debt and primary-balance observations establish the starting position. Monte Carlo bands reflect registered assumption ranges, not estimated confidence intervals; all results remain conditional scenarios rather than forecasts.",
                }],
            },
        ],
    }
    capex_indicator_order = (
        "capex-policy-input",
        "capex-sector-delivery",
        "capex-investment-quality",
        "capex-market-transmission",
        "capex-lag-test",
        "capex-corporate-case-study",
        "capex-real-conversion",
        "capex-crowding-in-depth",
        "capex-state-evaluation",
        "capex-fiscal-constraint",
        "capex-scenario-lab",
    )
    capex_section["indicators"] = sorted(
        capex_section["indicators"],
        key=lambda indicator: capex_indicator_order.index(indicator["id"]),
    )
    catalogue["sections"] = [capex_section]
    catalogue["generated_at"] = datetime.now(timezone.utc).isoformat()
    catalogue["roadmap_total"] = sum(len(section["indicators"]) for section in catalogue["sections"])
    return catalogue


def _capex_view(view_id, label, asset_id, visible, style, *, series_toggle=False, zero_line=False):
    value_format = (
        {"style": "number", "scale": 1, "decimals": 0, "prefix": "₹", "suffix": " cr"}
        if style == "crore"
        else {"style": style, "scale": 1, "decimals": 1}
    )
    return {
        "id": view_id,
        "label": label,
        "asset_id": asset_id,
        "presentation": {
            "component": "multi-series-line",
            "chart_type": "line",
            "x_axis": "date",
            "default_visible": visible,
            "value_format": value_format,
            "controls": {
                "date_range": True,
                "entity_toggle": False,
                "series_toggle": series_toggle,
            },
            "zero_line": zero_line,
            "show_source": True,
            "show_methodology": True,
        },
        "note": "Descriptive evidence; common movements do not identify a causal effect of public CapEx.",
    }


def main() -> None:
    with CATALOGUE_PATH.open(encoding="utf-8") as catalogue_file:
        catalogue = json.load(catalogue_file)
    payload = build_catalogue(catalogue, public_data_dir=CATALOGUE_PATH.parent)
    validate_payload(payload, "catalogue.schema.json", schema_dir=FRONTEND_SCHEMA_DIR)
    write_json_atomic(payload, CATALOGUE_PATH)
    print(f"updated {CATALOGUE_PATH} with the CapEx transmission story")


if __name__ == "__main__":
    main()
