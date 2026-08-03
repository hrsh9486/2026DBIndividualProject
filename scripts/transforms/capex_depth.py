"""Pure transformations for investment quality, state evaluation and crowding-in."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from extractors.rbi_handbook import RbiHandbookResponse
from helper import clean_float


_SECTOR = re.compile(r"^(?:\d+\.\s*)?(.*)$")
_FISCAL_YEAR = re.compile(r"^(\d{4})-(\d{2})(?:\s*\((A|RE|BE)\))?$")


def _normalise_sector(value: str) -> str:
    return _SECTOR.match(value.strip()).group(1).strip().lower()  # type: ignore[union-attr]


def _dated(year: int, value: float | None, *, status: str = "actual") -> dict:
    return {
        "date": f"{year}-03-31",
        "period_label": f"FY{year - 1}-{str(year)[-2:]}",
        "value": clean_float(value),
        "status": status,
    }


def _project_blocks(response: RbiHandbookResponse, row_names: tuple[str, ...]) -> dict:
    result: dict[str, dict[int, dict[str, float | None]]] = {}
    for sheet in response.sheets:
        header = next(
            (row for row in sheet.rows if row and str(row[0]).lower().startswith("sector")),
            None,
        )
        if header is None:
            continue
        years = [int(value) for value in header[1:] if isinstance(value, (int, float))]
        rows = sheet.rows
        for index, row in enumerate(rows):
            if not row or not isinstance(row[0], str):
                continue
            label = row[0].strip()
            if label != "Total" and not re.match(r"^\d+\.\s*", label):
                continue
            sector = "all sectors" if label == "Total" else _normalise_sector(label)
            metrics: dict[int, dict[str, float | None]] = {
                year: {} for year in years
            }
            for offset, metric in enumerate(row_names, start=1):
                if index + offset >= len(rows):
                    break
                values = rows[index + offset][1:]
                for year, value in zip(years, values):
                    metrics[year][metric] = (
                        float(value) if isinstance(value, (int, float)) else None
                    )
            result[sector] = metrics
    return result


def build_investment_quality_payload(
    status_response: RbiHandbookResponse,
    overrun_response: RbiHandbookResponse,
) -> dict:
    """Build comparable status and cost-efficiency measures by sector and year."""
    status = _project_blocks(
        status_response,
        ("ahead", "on_schedule", "delayed", "without_commissioning_date"),
    )
    costs = _project_blocks(
        overrun_response,
        ("projects_with_overrun", "original_cost", "anticipated_cost", "cost_overrun"),
    )
    sector_quality = []
    for sector in sorted(set(status) | set(costs)):
        years = sorted(set(status.get(sector, {})) | set(costs.get(sector, {})))
        for year in years:
            status_row = status.get(sector, {}).get(year, {})
            cost_row = costs.get(sector, {}).get(year, {})
            monitored = sum(
                value or 0 for value in (
                    status_row.get("ahead"),
                    status_row.get("on_schedule"),
                    status_row.get("delayed"),
                    status_row.get("without_commissioning_date"),
                )
            )
            original = cost_row.get("original_cost")
            overrun = cost_row.get("cost_overrun")
            sector_quality.append({
                "sector": sector,
                "year": year,
                "date": f"{year}-03-31",
                "projects_monitored": clean_float(monitored) if monitored else None,
                "on_schedule_share": clean_float(
                    ((status_row.get("ahead") or 0) + (status_row.get("on_schedule") or 0))
                    / monitored * 100
                ) if monitored else None,
                "delayed_share": clean_float(
                    (status_row.get("delayed") or 0) / monitored * 100
                ) if monitored else None,
                "without_date_share": clean_float(
                    (status_row.get("without_commissioning_date") or 0)
                    / monitored * 100
                ) if monitored else None,
                "original_cost_crore": clean_float(original),
                "anticipated_cost_crore": clean_float(cost_row.get("anticipated_cost")),
                "cost_overrun_crore": clean_float(overrun),
                "cost_overrun_pct": clean_float(overrun / original * 100)
                if original not in (None, 0) and overrun is not None else None,
            })

    aggregate = [row for row in sector_quality if row["sector"] == "all sectors"]
    metrics = {
        "projects_monitored": ("Projects monitored", "number"),
        "on_schedule_share": ("Ahead or on-schedule projects", "percent"),
        "delayed_share": ("Delayed projects", "percent"),
        "without_date_share": ("Projects without commissioning date", "percent"),
        "cost_overrun_pct": ("Cost overrun of delayed projects", "percent"),
    }
    series = {}
    for key, (label, unit) in metrics.items():
        values = [
            _dated(row["year"], row[key]) for row in aggregate
            if row.get(key) is not None
        ]
        series[key] = {
            "label": label,
            "entity": "IND",
            "unit": unit,
            "is_derived": key != "projects_monitored",
            "methodology": (
                "Share of monitored projects in the stated delivery category."
                if key.endswith("share") else
                "Anticipated less original cost, divided by original cost, for delayed projects."
                if key == "cost_overrun_pct" else
                "Central sector projects in the published monitoring universe."
            ),
            "source_note": "The monitoring threshold and delay definition changed in 2011; levels are descriptive, not a causal performance ranking.",
            "values": values,
        }
    dates = [row["date"] for item in series.values() for row in item["values"]]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [
                {"name": status_response.table_label, "url": status_response.source_url, "retrieved_at": status_response.retrieved_at},
                {"name": overrun_response.table_label, "url": overrun_response.source_url, "retrieved_at": overrun_response.retrieved_at},
            ],
            "frequency": "annual",
            "start_date": min(dates),
            "end_date": max(dates),
            "indicator_code": "CAPEX_INVESTMENT_QUALITY",
            "label": "Central-sector project implementation quality",
            "default_unit": "percent",
            "series_order": list(series),
            "is_derived": True,
            "methodology": "Published project-status counts are converted to shares. Cost overrun is anticipated less original cost as a share of original cost. Sector histories remain in metadata for the interactive explorer.",
            "note": "Coverage is central-sector projects of ₹100 crore and above through 2010 and ₹150 crore and above from 2011. This stage measures monitored delivery quality, not the social return or construction quality of completed assets.",
            "sector_quality": sector_quality,
            "break_note": "From 2011 the threshold rose from ₹100 crore to ₹150 crore and delay began to be measured against the original schedule.",
        },
        "series": series,
    }


def _parse_state_matrix(response: RbiHandbookResponse) -> dict[str, dict[str, float]]:
    values: dict[str, dict[str, float]] = {}
    for sheet in response.sheets:
        header_index = next(
            (index for index, row in enumerate(sheet.rows) if row and all(
                isinstance(value, str) and _FISCAL_YEAR.match(value)
                for value in row if value is not None
            ) and len(row) >= 3),
            None,
        )
        if header_index is None:
            continue
        years = [str(value) for value in sheet.rows[header_index]]
        for row in sheet.rows[header_index + 1:]:
            if not row or not isinstance(row[0], str) or row[0].startswith(("Note", "Source")):
                continue
            state = row[0].strip()
            if state.lower().startswith(("all india", "states", "union territories")):
                continue
            for year, value in zip(years, row[1:]):
                if isinstance(value, (int, float)):
                    values.setdefault(state, {})[year] = float(value)
    return values


def _parse_capital_outlay(response: RbiHandbookResponse) -> dict[str, dict[str, tuple[float, str]]]:
    values: dict[str, dict[str, tuple[float, str]]] = {}
    for sheet in response.sheets:
        header_index = next(
            (index for index, row in enumerate(sheet.rows) if row and row[0] == "State/Union Territory"),
            None,
        )
        if header_index is None:
            continue
        years = [str(value) for value in sheet.rows[header_index][1:]]
        for row in sheet.rows[header_index + 1:]:
            if not row or not isinstance(row[0], str) or row[0].startswith(("Note", "Source")):
                continue
            state = row[0].strip()
            for label, value in zip(years, row[1:]):
                match = _FISCAL_YEAR.match(label)
                if not match or not isinstance(value, (int, float)):
                    continue
                status = {None: "actual", "A": "actual", "RE": "revised", "BE": "budget"}[match.group(3)]
                values.setdefault(state, {})[f"{match.group(1)}-{match.group(2)}"] = (float(value), status)
    return values


def _two_way_within(frame: pd.DataFrame) -> dict:
    work = frame.copy()
    for column in ("x", "y"):
        work[f"{column}w"] = (
            work[column]
            - work.groupby("state")[column].transform("mean")
            - work.groupby("year")[column].transform("mean")
            + work[column].mean()
        )
    denominator = float((work["xw"] ** 2).sum())
    beta = float((work["xw"] * work["yw"]).sum() / denominator) if denominator else math.nan
    residual = work["yw"] - beta * work["xw"]
    clusters = work.assign(score=work["xw"] * residual).groupby("state")["score"].sum()
    groups = len(clusters)
    n = len(work)
    correction = (groups / (groups - 1)) * ((n - 1) / max(n - 1, 1)) if groups > 1 else math.nan
    variance = correction * float((clusters ** 2).sum()) / denominator ** 2 if denominator and groups > 1 else math.nan
    se = math.sqrt(max(variance, 0)) if math.isfinite(variance) else math.nan
    return {
        "coefficient": clean_float(beta),
        "clustered_standard_error": clean_float(se),
        "confidence_interval_95": [clean_float(beta - 1.96 * se), clean_float(beta + 1.96 * se)] if math.isfinite(se) else None,
        "n": n,
        "states": int(work["state"].nunique()),
        "years": int(work["year"].nunique()),
    }


def build_state_capex_evaluation_payload(
    current_gsdp_response: RbiHandbookResponse,
    constant_gsdp_response: RbiHandbookResponse,
    capital_outlay_response: RbiHandbookResponse,
) -> dict:
    """Build a state-year panel and a transparent two-way fixed-effects estimate."""
    current = _parse_state_matrix(current_gsdp_response)
    constant = _parse_state_matrix(constant_gsdp_response)
    outlay = _parse_capital_outlay(capital_outlay_response)
    observations = []
    for state in sorted(set(current) & set(constant) & set(outlay)):
        for fiscal_year, (capital, status) in sorted(outlay[state].items()):
            if status != "actual" or fiscal_year not in current[state] or fiscal_year not in constant[state]:
                continue
            start = int(fiscal_year[:4])
            next_year = f"{start + 1}-{str(start + 2)[-2:]}"
            if next_year not in constant[state] or constant[state][fiscal_year] == 0:
                continue
            intensity = capital * 10000 / current[state][fiscal_year]
            next_growth = (constant[state][next_year] / constant[state][fiscal_year] - 1) * 100
            observations.append({
                "state": state,
                "year": start + 1,
                "date": f"{start + 1}-03-31",
                "period_label": f"FY{fiscal_year}",
                "capex_pct_gsdp": clean_float(intensity),
                "next_year_real_gsdp_growth": clean_float(next_growth),
                "status": status,
            })
    frame = pd.DataFrame({
        "state": [row["state"] for row in observations],
        "year": [row["year"] for row in observations],
        "x": [row["capex_pct_gsdp"] for row in observations],
        "y": [row["next_year_real_gsdp_growth"] for row in observations],
    }).dropna()
    estimate = _two_way_within(frame)
    required = {"observations": 100, "states": 15, "years": 5}
    eligible = (
        estimate["n"] >= required["observations"]
        and estimate["states"] >= required["states"]
        and estimate["years"] >= required["years"]
    )
    estimate.update({
        "eligible": eligible,
        "required": required,
        "evidence_class": "associational",
        "interpretation": "Within-state change in next-year real GSDP growth associated with a one percentage-point change in capital outlay/GSDP after removing common year effects.",
        "limitation": "State and year fixed effects do not remove time-varying policy choices, disasters, transfers, project selection or reverse causality; this is not a causal multiplier.",
    })
    medians = frame.groupby("year")[["x", "y"]].median().reset_index()
    series = {
        "median_state_capex_pct_gsdp": {
            "label": "Median state capital outlay/GSDP",
            "entity": "IND_STATES",
            "unit": "percent",
            "is_derived": True,
            "methodology": "Cross-state median of capital outlay divided by current-price GSDP.",
            "source_note": "State accounting coverage and budget status vary; only observations labelled actual are used in the panel estimate.",
            "values": [_dated(int(row.year), float(row.x)) for row in medians.itertuples()],
        },
        "median_next_year_real_gsdp_growth": {
            "label": "Median next-year real GSDP growth",
            "entity": "IND_STATES",
            "unit": "percent",
            "is_derived": True,
            "methodology": "Cross-state median of the subsequent fiscal year's constant-price GSDP growth.",
            "source_note": "Growth is an outcome association, not a project-level return.",
            "values": [_dated(int(row.year), float(row.y)) for row in medians.itertuples()],
        },
    }
    dates = [row["date"] for row in observations]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [
                {"name": current_gsdp_response.table_label, "url": current_gsdp_response.source_url, "retrieved_at": current_gsdp_response.retrieved_at},
                {"name": constant_gsdp_response.table_label, "url": constant_gsdp_response.source_url, "retrieved_at": constant_gsdp_response.retrieved_at},
                {"name": capital_outlay_response.table_label, "url": capital_outlay_response.source_url, "retrieved_at": capital_outlay_response.retrieved_at},
            ],
            "frequency": "annual",
            "start_date": min(dates),
            "end_date": max(dates),
            "indicator_code": "STATE_CAPEX_EVALUATION_PANEL",
            "label": "State capital outlay and subsequent real growth",
            "default_unit": "percent",
            "series_order": list(series),
            "is_derived": True,
            "methodology": "Actual state capital outlay is scaled by current-price GSDP and paired with next-year constant-price GSDP growth. The registered estimate uses state and fiscal-year fixed effects with state-clustered standard errors.",
            "note": "This is a state-year associational evaluation. It deliberately does not claim project-level or causal identification.",
            "panel_observations": observations,
            "panel_estimate": estimate,
        },
        "series": series,
    }


def _annual_series(payload: dict, key: str, *, fiscalise_quarters: bool = False) -> pd.Series:
    rows = payload["series"][key]["values"]
    values = pd.Series(
        {pd.Timestamp(row["date"]): row["value"] for row in rows if row.get("value") is not None},
        dtype=float,
    ).sort_index()
    if fiscalise_quarters:
        fiscal_end = values.index.map(lambda date: date.year + 1 if date.month > 3 else date.year)
        values = values.groupby(fiscal_end).mean()
        values.index = pd.DatetimeIndex([f"{year}-03-31" for year in values.index])
    return values


def build_crowding_in_payload(execution: dict, private: dict, production: dict) -> dict:
    """Create a distributed-lag evidence ladder with explicit sample gates."""
    capex = _annual_series(execution, "capex_actual").pct_change(fill_method=None) * 100
    outcomes = {
        "private_gfcf": (
            "Private corporate GFCF/GDP",
            _annual_series(private, "private_corporate_gfcf_pct_gdp"),
            "level",
            "Direct private-investment outcome",
        ),
        "private_gfcf_share": (
            "Private corporate share of total GFCF",
            _annual_series(private, "private_share_total_gfcf"),
            "level",
            "Direct private-investment composition outcome",
        ),
        "capacity_utilisation": (
            "Manufacturing capacity utilisation",
            _annual_series(private, "manufacturing_capacity_utilisation", fiscalise_quarters=True),
            "level",
            "Operating-capacity outcome",
        ),
        "capital_goods_iip_growth": (
            "Capital-goods production growth",
            _annual_series(production, "capital_goods_iip").pct_change(fill_method=None) * 100,
            "growth",
            "Upstream real-economy outcome; not direct private investment",
        ),
    }
    estimates = []
    pair_rows = []
    series = {
        "nominal_capex_growth": {
            "label": "Actual nominal central CapEx growth",
            "entity": "IND",
            "unit": "percent",
            "is_derived": True,
            "methodology": "Year-on-year growth in actual nominal central-government capital expenditure.",
            "source_note": "Nominal growth includes inflation and cannot identify an exogenous public-investment shock.",
            "values": [_dated(date.year, float(value)) for date, value in capex.dropna().items()],
        }
    }
    for outcome_key, (label, outcome, transformation, role) in outcomes.items():
        for lag in range(4):
            pairs = []
            for date, capex_growth in capex.dropna().items():
                outcome_date = date + pd.DateOffset(years=lag)
                if outcome_date not in outcome.index or pd.isna(outcome.loc[outcome_date]):
                    continue
                pairs.append((date, float(capex_growth), float(outcome.loc[outcome_date])))
            frame = pd.DataFrame(pairs, columns=["date", "capex_growth", "outcome"])
            pearson = frame[["capex_growth", "outcome"]].corr(method="pearson").iloc[0, 1] if len(frame) >= 3 else math.nan
            spearman = frame[["capex_growth", "outcome"]].corr(method="spearman").iloc[0, 1] if len(frame) >= 3 else math.nan
            eligible = len(frame) >= 8
            estimate = {
                "key": f"{outcome_key}_lag_{lag}y",
                "outcome_key": outcome_key,
                "label": label,
                "role": role,
                "transformation": transformation,
                "lag": lag,
                "lag_unit": "years",
                "n": len(frame),
                "pearson": clean_float(pearson),
                "spearman": clean_float(spearman),
                "eligible": eligible,
                "required_observations": 8,
                "status": "associational" if eligible else "insufficient_data",
            }
            estimates.append(estimate)
            for row in frame.itertuples():
                pair_rows.append({
                    "estimate_key": estimate["key"],
                    "date": row.date.strftime("%Y-%m-%d"),
                    "capex_growth": clean_float(row.capex_growth),
                    "outcome": clean_float(row.outcome),
                })
    dates = [row["date"] for row in series["nominal_capex_growth"]["values"]]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [
                {"name": "Validated central-government CapEx artifact"},
                {"name": "Validated private-investment and capacity artifact"},
                {"name": "Validated capital-goods production artifact"},
            ],
            "frequency": "annual",
            "start_date": min(dates),
            "end_date": max(dates),
            "indicator_code": "CAPEX_CROWDING_IN_DISTRIBUTED_LAGS",
            "label": "Crowding-in distributed-lag evidence ladder",
            "default_unit": "percent",
            "series_order": list(series),
            "is_derived": True,
            "methodology": "Nominal CapEx growth is paired with four outcomes at zero- through three-year leads. Pearson and Spearman correlations are published only as associations and every cell is gated at eight aligned annual observations.",
            "note": "The current national-accounts vintages do not meet the registered minimum sample for a credible crowding-in estimate. Showing that failure is preferable to presenting unstable coefficients as evidence.",
            "lag_estimates": estimates,
            "pair_observations": pair_rows,
        },
        "series": series,
    }
