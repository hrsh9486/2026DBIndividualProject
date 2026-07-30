"""Build and publish the complete India public-CapEx transmission project."""

from __future__ import annotations

import argparse
import json
import logging
from copy import deepcopy
from pathlib import Path

import pandas as pd

from config import PROCESSED_DATA_DIR
from config.capex_analysis import (
    ANALYSIS_START,
    CAPEX_MARKETS,
    CORPORATE_CASES,
    OUTPUTS,
)
from exporters import publish_json
from extractors.nifty_indices import NiftyIndicesExtractor
from extractors.corporate_fundamentals import CorporateFundamentalsExtractor
from transforms.capex_analysis import (
    build_lag_analysis,
    build_sector_performance_payload,
    classify_summary,
)
from transforms.corporate_fundamentals import build_corporate_fundamentals_payload
from validators import validate_payload


LOGGER = logging.getLogger(__name__)
STRUCTURAL_INPUTS = {
    "execution": PROCESSED_DATA_DIR / "government-investment" / "capex-and-execution.json",
    "private": PROCESSED_DATA_DIR / "private-investment" / "investment-and-capacity.json",
    "fiscal": PROCESSED_DATA_DIR / "fiscal-capacity" / "debt-and-interest-burden.json",
}


def _load_validated(path: Path, schema: str = "dated_multi_series.schema.json") -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Required validated input does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_payload(payload, schema)
    return payload


def _scope_payload(payload: dict, series_keys: tuple[str, ...], start_date: str) -> dict:
    scoped = deepcopy(payload)
    scoped["series"] = {
        key: scoped["series"][key] for key in series_keys if key in scoped["series"]
    }
    scoped["metadata"]["series_order"] = list(scoped["series"])
    for series in scoped["series"].values():
        series["values"] = [
            row for row in series["values"] if row["date"] >= start_date
        ]
    dates = [
        row["date"] for series in scoped["series"].values() for row in series["values"]
    ]
    if not dates:
        raise ValueError("Scope filter removed every observation")
    scoped["metadata"]["start_date"] = min(dates)
    scoped["metadata"]["end_date"] = max(dates)
    return scoped


def _add_capex_growth(payload: dict) -> dict:
    scoped = deepcopy(payload)
    rows = scoped["series"]["capex_actual"]["values"]
    growth = []
    previous = None
    for row in rows:
        value = row.get("value")
        derived = deepcopy(row)
        derived["value"] = (
            None if previous in (None, 0) or value is None
            else (value / previous - 1) * 100
        )
        growth.append(derived)
        if value is not None:
            previous = value
    scoped["series"]["nominal_capex_growth"] = {
        "label": "Actual CapEx growth",
        "entity": "IND",
        "unit": "percent",
        "is_derived": True,
        "methodology": "Year-on-year percentage change in actual nominal central-government capital expenditure.",
        "source_note": "Nominal growth is affected by inflation and does not measure project quality.",
        "values": growth,
    }
    scoped["metadata"]["series_order"].append("nominal_capex_growth")
    scoped["metadata"]["note"] = (
        f"{scoped['metadata'].get('note', '')} Real CapEx growth is not published until "
        "a consistent government-investment deflator is registered; nominal growth is explicitly labelled."
    ).strip()
    return scoped


def _add_fiscal_bridge(fiscal_payload: dict, execution_payload: dict) -> dict:
    payload = deepcopy(fiscal_payload)
    capex = deepcopy(execution_payload["series"]["actual_capex_pct_total_expenditure"])
    capex["label"] = "Actual CapEx as share of expenditure"
    payload["series"]["actual_capex_pct_expenditure"] = capex
    interest = {
        row["date"]: row
        for row in payload["series"]["interest_payments_pct_expenditure"]["values"]
        if row.get("value") is not None
    }
    ratio_values = []
    for row in capex["values"]:
        matching = interest.get(row["date"])
        if row.get("value") is None or not matching or matching["value"] == 0:
            continue
        ratio_values.append({
            "date": row["date"],
            "period_label": row.get("period_label", matching.get("period_label")),
            "value": row["value"] / matching["value"],
            "status": (
                matching.get("status", "actual")
                if matching.get("status") != "actual"
                else row.get("status", "actual")
            ),
        })
    payload["series"]["capex_to_interest_allocation_ratio"] = {
        "label": "CapEx-to-interest allocation ratio",
        "entity": "IND",
        "unit": "ratio",
        "is_derived": True,
        "methodology": "Actual CapEx share of total expenditure divided by interest payments share of total expenditure.",
        "source_note": "This is an expenditure-allocation ratio, not a benefit-cost ratio or debt-sustainability threshold.",
        "values": ratio_values,
    }
    payload["metadata"]["series_order"].extend([
        "actual_capex_pct_expenditure",
        "capex_to_interest_allocation_ratio",
    ])
    payload["metadata"]["start_date"] = min(
        row["date"] for item in payload["series"].values() for row in item["values"]
    )
    payload["metadata"]["end_date"] = max(
        row["date"] for item in payload["series"].values() for row in item["values"]
    )
    return payload


def build_all(
    prices: pd.DataFrame,
    execution: dict,
    private: dict,
    fiscal: dict,
    *,
    corporate_records=(),
) -> dict[str, dict]:
    definitions = {
        market.key: {
            "label": market.label,
            "ticker": market.ticker,
            "role": market.role,
        }
        for market in CAPEX_MARKETS
    }
    sector = build_sector_performance_payload(prices, definitions)
    correlations, estimates = build_lag_analysis(execution, sector, private)
    execution_output = _add_capex_growth(_scope_payload(
        execution,
        (
            "actual_capex_pct_gdp",
            "actual_capex_pct_total_expenditure",
            "capex_execution_ratio",
            "capex_budget_estimate",
            "capex_revised_estimate",
            "capex_actual",
        ),
        "2018-03-31",
    ))
    private_output = _scope_payload(
        private,
        (
            "private_corporate_gfcf_pct_gdp",
            "private_share_total_gfcf",
            "manufacturing_capacity_utilisation",
            "public_capex_lagged",
        ),
        "2018-03-31",
    )
    fiscal_output = _scope_payload(
        fiscal,
        (
            "general_government_debt_pct_gdp",
            "interest_payments_pct_revenue",
            "interest_payments_pct_expenditure",
            "primary_balance_pct_gdp",
        ),
        "2011-03-31",
    )
    fiscal_output = _add_fiscal_bridge(fiscal_output, execution_output)
    summary = classify_summary(execution_output, private_output, fiscal_output, estimates)
    fiscal_output["metadata"]["transmission_evidence"] = [
        {
            "key": item["key"],
            "status": item["status"],
            "interpretation": item["interpretation"],
        }
        for item in summary["hypotheses"]
    ]
    payloads = {
        "execution": execution_output,
        "sectors": sector,
        "correlations": correlations,
        "private": private_output,
        "fiscal": fiscal_output,
        "summary": summary,
    }
    if corporate_records:
        payloads["corporate"] = build_corporate_fundamentals_payload(tuple(corporate_records))
    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prices-json",
        type=Path,
        help="Optional landed price matrix for reproducible/offline builds.",
    )
    parser.add_argument(
        "--skip-corporate",
        action="store_true",
        help="Build the pre-existing analysis without refreshing corporate statements.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    structural = {key: _load_validated(path) for key, path in STRUCTURAL_INPUTS.items()}
    if args.prices_json:
        raw = json.loads(args.prices_json.read_text(encoding="utf-8"))
        prices = pd.DataFrame(raw["values"], index=pd.to_datetime(raw["dates"]))
    else:
        prices = NiftyIndicesExtractor().fetch_total_return_indices(
            {market.key: market.ticker for market in CAPEX_MARKETS},
            start_year=2018,
        )
    prices.index = pd.to_datetime(prices.index)
    prices = prices.loc[pd.Timestamp(ANALYSIS_START):]
    corporate_records = (
        ()
        if args.skip_corporate
        else CorporateFundamentalsExtractor().fetch(CORPORATE_CASES)
    )
    payloads = build_all(
        prices,
        structural["execution"],
        structural["private"],
        structural["fiscal"],
        corporate_records=corporate_records,
    )
    schemas = {
        "execution": "dated_multi_series.schema.json",
        "sectors": "market_performance.schema.json",
        "correlations": "dated_multi_series.schema.json",
        "private": "dated_multi_series.schema.json",
        "fiscal": "dated_multi_series.schema.json",
        "summary": "capex_analysis_summary.schema.json",
        "corporate": "dated_multi_series.schema.json",
    }
    for key, payload in payloads.items():
        destination = PROCESSED_DATA_DIR / OUTPUTS[key]
        publish_json(payload, destination, schemas[key])
        LOGGER.info("Published %s", destination)


if __name__ == "__main__":
    main()
