"""Aggregate the frozen corporate case study without market-cap weighting."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from helper import clean_float
from models.capex_sources import CorporateFundamental


GROWTH_FIELDS = ("revenue", "ebitda", "capex", "net_ppe", "debt")
METRICS = (
    ("revenue_growth", "Revenue growth", "percent"),
    ("ebitda_growth", "EBITDA growth", "percent"),
    ("capex_growth", "Corporate CapEx growth", "percent"),
    ("net_ppe_growth", "Net PPE growth", "percent"),
    ("roce_proxy", "ROCE proxy", "percent"),
    ("debt_growth", "Debt growth", "percent"),
)


def build_corporate_fundamentals_payload(
    records: tuple[CorporateFundamental, ...],
) -> dict:
    rows = [{
        "company_key": record.company_key,
        "company_label": record.company_label,
        "group": record.group,
        "date": record.fiscal_end,
        "year": record.fiscal_end.year,
        "revenue": record.revenue,
        "ebitda": record.ebitda,
        "capex": record.capex,
        "net_ppe": record.net_ppe,
        "debt": record.debt,
        "roce_proxy": record.roce_proxy,
    } for record in records]
    frame = pd.DataFrame(rows).sort_values(["company_key", "date"])
    for field in GROWTH_FIELDS:
        frame[f"{field}_growth"] = frame.groupby("company_key")[field].pct_change(fill_method=None) * 100
    series = {}
    group_labels = {"capital_goods": "Capital-goods companies", "infrastructure": "Infrastructure companies"}
    for group, group_label in group_labels.items():
        subset = frame[frame["group"] == group]
        for metric, metric_label, unit in METRICS:
            values = []
            for year, annual in subset.groupby("year"):
                observations = annual[metric].replace([np.inf, -np.inf], np.nan).dropna()
                if observations.empty:
                    continue
                values.append({
                    "date": f"{int(year)}-03-31",
                    "period_label": f"Reporting year {int(year)}",
                    "value": clean_float(observations.median()),
                    "status": "actual",
                })
            key = f"{group}_{metric}"
            series[key] = {
                "label": f"{group_label}: median {metric_label.lower()}",
                "entity": "IND",
                "unit": unit,
                "is_derived": True,
                "methodology": "Unweighted median across the frozen five-company group; growth is calculated company by company before aggregation.",
                "source_note": "Reporting dates and accounting classifications differ across companies; the basket is a case study, not the full index.",
                "values": values,
            }
    dates = [row["date"] for item in series.values() for row in item["values"]]
    if not dates:
        raise ValueError("Corporate fundamentals produced no aggregate observations")
    coverage = [
        {
            "company_key": key,
            "company": company.iloc[0]["company_label"],
            "group": company.iloc[0]["group"],
            "start_year": int(company["year"].min()),
            "end_year": int(company["year"].max()),
            "observations": int(len(company)),
        }
        for key, company in frame.groupby("company_key")
    ]
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [{"name": "Company annual financial statements via Yahoo Finance"}],
            "frequency": "annual",
            "start_date": min(dates),
            "end_date": max(dates),
            "indicator_code": "CAPEX_CORPORATE_FUNDAMENTALS_CASE_STUDY",
            "label": "Corporate fundamentals of CapEx-sensitive companies",
            "default_unit": "percent",
            "series_order": list(series),
            "is_derived": True,
            "methodology": "Five frozen capital-goods and five frozen infrastructure companies. All level growth rates are calculated within company and aggregated using the group median.",
            "note": "Order-book data are excluded because consistent machine-readable histories are unavailable. ROCE is a proxy using EBIT divided by total assets less current liabilities.",
            "company_coverage": coverage,
        },
        "series": series,
    }
