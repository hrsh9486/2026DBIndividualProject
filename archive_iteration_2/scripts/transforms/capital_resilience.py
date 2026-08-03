"""Aggregate archived NSE institutional flows into monthly resilience measures."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from extractors.nse_institutional_flows import NseInstitutionalFlowResponse
from models import CanonicalRecord, ObservationStatus


def _is_consecutive_months(months: list[tuple[int, int]]) -> bool:
    return all(
        current[0] * 12 + current[1] == previous[0] * 12 + previous[1] + 1
        for previous, current in zip(months, months[1:])
    )


def build_capital_resilience_records(response: NseInstitutionalFlowResponse) -> list[CanonicalRecord]:
    monthly: dict[tuple[int, int], dict[str, float]] = defaultdict(lambda: {"DII": 0.0, "FPI": 0.0})
    latest_date: dict[tuple[int, int], date] = {}
    for item in response.observations:
        key = (item.date.year, item.date.month)
        monthly[key][item.category] += item.net_crore
        latest_date[key] = max(item.date, latest_date.get(key, item.date))

    months = sorted(monthly)
    records: list[CanonicalRecord] = []
    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    for index, month in enumerate(months):
        values = monthly[month]
        observation_date = latest_date[month]
        common = {
            "date": observation_date,
            "entity": "IND",
            "frequency": "monthly",
            "source": "NSE provisional FII/FPI and DII trading activity",
            "status": ObservationStatus.PROVISIONAL,
            "period_label": observation_date.strftime("%b %Y"),
            "source_url": response.source_url,
            "retrieved_at": retrieved_at,
        }
        records.extend((
            CanonicalRecord(indicator="dii_net_flow", value=values["DII"], unit="INR_crore", **common),
            CanonicalRecord(indicator="fpi_net_flow", value=values["FPI"], unit="INR_crore", **common),
        ))
        window_months = months[index - 11:index + 1] if index >= 11 else []
        has_window = len(window_months) == 12 and _is_consecutive_months(window_months)
        records.extend((
            CanonicalRecord(
                indicator="dii_rolling_12m",
                value=sum(monthly[key]["DII"] for key in window_months) if has_window else None,
                unit="INR_crore",
                is_derived=True,
                method="Trailing sum of 12 consecutive monthly DII net flows",
                **common,
            ),
            CanonicalRecord(
                indicator="fpi_rolling_12m",
                value=sum(monthly[key]["FPI"] for key in window_months) if has_window else None,
                unit="INR_crore",
                is_derived=True,
                method="Trailing sum of 12 consecutive monthly FPI net flows",
                **common,
            ),
            CanonicalRecord(
                indicator="dii_offset_ratio",
                value=max(values["DII"], 0) / abs(values["FPI"]) if values["FPI"] < 0 else None,
                unit="ratio",
                is_derived=True,
                method="Positive DII net buying / absolute FPI net selling; null outside FPI-selling months",
                **common,
            ),
        ))
    return records
