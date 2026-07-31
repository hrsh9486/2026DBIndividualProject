"""Add the focused research programme to the static frontend catalogue.

Existing non-focused sections and assets are preserved until their removal is
explicitly approved. Focused bundles without a promoted artifact are exposed
as planned work rather than as empty live datasets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import PROJECT_ROOT
from config.evidence_specs import EVIDENCE_OUTPUT_PATHS
from config.capex_analysis import OUTPUTS as CAPEX_OUTPUTS
from config.focused_indicators import FOCUSED_BUNDLES, FocusedSeriesSpec
from exporters import write_json_atomic
from validators import validate_evidence_report, validate_payload


CATALOGUE_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "catalogue.json"
FRONTEND_SCHEMA_DIR = PROJECT_ROOT / "frontend" / "public" / "data" / "schemas"


def _slug(value: str) -> str:
    return value.replace("_", "-")


def _value_format(series: FocusedSeriesSpec) -> dict:
    if series.unit in {"percent", "percentage_points"}:
        return {"style": "percent", "scale": 1, "decimals": 1}
    if series.unit == "INR":
        return {"style": "currency", "scale": 1, "decimals": 0, "currency": "INR"}
    if series.unit == "INR_crore":
        return {"style": "number", "scale": 1, "decimals": 0, "prefix": "₹", "suffix": " cr"}
    if series.unit == "index":
        return {"style": "index", "scale": 1, "decimals": 1}
    if series.unit == "ratio":
        return {"style": "ratio", "scale": 1, "decimals": 2}
    return {"style": "number", "scale": 1, "decimals": 2}


def _stale_after_days(frequency: str) -> int:
    return {"monthly": 45, "annual": 450, "mixed": 120}.get(frequency, 120)


def _artifact_availability(path: Path, bundle) -> str:
    if not path.is_file():
        return "planned"
    try:
        with path.open(encoding="utf-8") as artifact_file:
            artifact = json.load(artifact_file)
        series = artifact["series"]
        complete = all(
            any(observation.get("value") is not None for observation in series[spec.key]["values"])
            for spec in bundle.series
        )
    except (KeyError, TypeError, json.JSONDecodeError):
        return "partial"
    return "active" if complete else "partial"


def _section(
    bundle,
    *,
    order: int,
    asset_id: str,
    evidence_asset_id: str | None = None,
) -> dict:
    indicators = []
    zero_line_series = {
        "gst_growth_gap",
        "primary_balance_pct_gdp",
        "reer_deviation_pct",
        "current_account_pct_gdp",
        "non_oil_export_growth",
        "dii_net_flow",
        "fpi_net_flow",
        "dii_rolling_12m",
        "fpi_rolling_12m",
    }
    for series in bundle.series:
        indicators.append({
            "id": _slug(series.key),
            "title": series.label,
            "summary": series.definition,
            "default_view": "main",
            "views": [{
                "id": "main",
                "label": "Time series",
                "asset_id": asset_id,
                "presentation": {
                    "component": "multi-series-line",
                    "chart_type": "line",
                    "x_axis": "date",
                    "default_visible": [series.key],
                    "value_format": _value_format(series),
                    "controls": {
                        "date_range": True,
                        "entity_toggle": False,
                        "series_toggle": False,
                    },
                    "zero_line": series.key in zero_line_series,
                    "show_source": True,
                    "show_methodology": True,
                },
                "note": series.limitation,
            }],
        })
    section = {
        "id": _slug(bundle.key),
        "label": bundle.label,
        "order": order,
        "indicators": indicators,
    }
    if evidence_asset_id is not None:
        section["evidence_asset_id"] = evidence_asset_id
    return section


def build_catalogue(catalogue: dict, *, public_data_dir: Path) -> dict:
    """Return a focused catalogue while retaining unrelated legacy entries."""
    focused_ids = {_slug(key) for key in FOCUSED_BUNDLES}
    existing_sections = [
        section for section in catalogue.get("sections", [])
        if section.get("id") not in focused_ids
        and section.get("id") != "capex-transmission"
    ]
    for section in existing_sections:
        if section.get("order", 0) <= len(FOCUSED_BUNDLES):
            section["order"] += len(FOCUSED_BUNDLES)

    focused_sections = []
    for order, bundle in enumerate(FOCUSED_BUNDLES.values(), start=1):
        asset_id = _slug(bundle.key)
        promoted = public_data_dir / bundle.output_path
        availability = _artifact_availability(promoted, bundle)
        catalogue.setdefault("assets", {})[asset_id] = {
            "data_path": f"/data/{bundle.output_path}",
            "schema_path": "/data/schemas/dated_multi_series.schema.json",
            "schema": "dated_multi_series",
            "expected_frequency": bundle.frequency,
            "stale_after_days": _stale_after_days(bundle.frequency),
            "cache_strategy": "revalidate",
            "version": datetime.now(timezone.utc).date().isoformat(),
            "availability": availability,
            "description": bundle.research_question,
        }
        evidence_asset_id = f"{asset_id}-evidence"
        evidence_relative_path = EVIDENCE_OUTPUT_PATHS[bundle.key]
        evidence_path = public_data_dir / evidence_relative_path
        if evidence_path.is_file():
            evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            validate_evidence_report(evidence_payload)
            catalogue["assets"][evidence_asset_id] = {
                "data_path": f"/data/{evidence_relative_path}",
                "schema_path": "/data/schemas/evidence_report.schema.json",
                "schema": "evidence_report",
                "expected_frequency": "mixed",
                "stale_after_days": 120,
                "cache_strategy": "revalidate",
                "version": evidence_payload["metadata"]["generated_at"],
                "availability": "active",
                "description": (
                    f"Registered statistical evidence for {bundle.label.lower()}."
                ),
            }
        else:
            catalogue["assets"].pop(evidence_asset_id, None)
            evidence_asset_id = None
        focused_sections.append(_section(
            bundle,
            order=order,
            asset_id=asset_id,
            evidence_asset_id=evidence_asset_id,
        ))

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
    }
    catalogue["assets"].pop("capex-sector-delivery", None)
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
                        "default_visible": ["CAPITAL_GOODS", "INFRASTRUCTURE", "MANUFACTURING"],
                        "value_format": {"style": "index", "scale": 1, "decimals": 1},
                        "controls": {"date_range": True, "entity_toggle": False, "series_toggle": True},
                        "zero_line": False, "show_source": True, "show_methodology": True,
                    },
                    "note": "Index provider data are preferred; the automated pipeline uses provider-labelled adjusted-close histories and preserves raw observations.",
                }, {
                    "id": "control", "label": "FMCG comparison", "asset_id": "capex-sector-performance",
                    "presentation": {
                        "component": "market-performance", "chart_type": "line", "x_axis": "date",
                        "market_field": "normalized_value",
                        "default_visible": ["CAPITAL_GOODS", "INFRASTRUCTURE", "MANUFACTURING", "FMCG"],
                        "value_format": {"style": "index", "scale": 1, "decimals": 1},
                        "controls": {"date_range": True, "entity_toggle": False, "series_toggle": True},
                        "zero_line": False, "show_source": True, "show_methodology": True,
                    },
                    "note": "Each official TRI is independently rebased to 100 at the common start date. The correlation analysis still uses target-sector returns relative to Nifty FMCG.",
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
                "summary": "Test when a sustained increase in public CapEx produces enough growth and revenue feedback to justify its financing burden.",
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
                    "note": "The latest non-budget fiscal observation establishes the starting position. Multipliers, lags, crowding effects and future financing conditions are editable assumptions—not estimates or forecasts.",
                }],
            },
        ],
    }
    capex_indicator_order = (
        "capex-policy-input",
        "capex-sector-delivery",
        "capex-market-transmission",
        "capex-lag-test",
        "capex-corporate-case-study",
        "capex-real-conversion",
        "capex-fiscal-constraint",
        "capex-scenario-lab",
    )
    capex_section["indicators"] = sorted(
        capex_section["indicators"],
        key=lambda indicator: capex_indicator_order.index(indicator["id"]),
    )
    for section in focused_sections + existing_sections:
        section["order"] = section.get("order", 0) + 1
    catalogue["sections"] = [capex_section] + focused_sections + existing_sections
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
    print(f"updated {CATALOGUE_PATH} with {len(FOCUSED_BUNDLES)} focused lenses")


if __name__ == "__main__":
    main()
