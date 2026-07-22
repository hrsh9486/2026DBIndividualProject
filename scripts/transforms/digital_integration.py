"""Deterministic digital-integration calculations."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Mapping, Sequence

from extractors.npci import UpiMonthlyRecord
from models import CanonicalRecord, ObservationStatus


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _consecutive_window(records: Sequence[UpiMonthlyRecord], end: int, size: int) -> Sequence[UpiMonthlyRecord] | None:
    if end + 1 < size:
        return None
    window = records[end + 1 - size:end + 1]
    month_numbers = [record.year * 12 + record.month for record in window]
    if any(right - left != 1 for left, right in zip(month_numbers, month_numbers[1:])):
        return None
    return window


def build_upi_canonical_records(
    upi_records: Sequence[UpiMonthlyRecord],
    *,
    population_by_year: Mapping[int, float],
    nominal_gdp_inr_by_year: Mapping[int, float],
    source_url: str,
    retrieved_at: datetime,
) -> list[CanonicalRecord]:
    """Create UPI per-capita, average-value and rolling-value/GDP records."""
    ordered = sorted(upi_records, key=lambda item: (item.year, item.month))
    output: list[CanonicalRecord] = []
    common = {
        "entity": "IND",
        "frequency": "monthly",
        "source": "NPCI; World Bank Indicators API",
        "status": ObservationStatus.ACTUAL,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "is_derived": True,
    }
    for index, record in enumerate(ordered):
        observation_date = _month_end(record.year, record.month)
        population = population_by_year.get(record.year)
        per_capita = record.volume_millions * 1_000_000 / population if population and population > 0 else None
        average_value = (
            record.value_crore * 10_000_000 / (record.volume_millions * 1_000_000)
            if record.volume_millions > 0 else None
        )
        window = _consecutive_window(ordered, index, 12)
        nominal_gdp = nominal_gdp_inr_by_year.get(record.year)
        value_pct_gdp = None
        if window and nominal_gdp and nominal_gdp > 0:
            trailing_value_inr = sum(item.value_crore for item in window) * 10_000_000
            value_pct_gdp = trailing_value_inr / nominal_gdp * 100

        output.extend((
            CanonicalRecord(date=observation_date, indicator="upi_transactions_per_capita", value=per_capita, unit="transactions_per_person", method="Monthly UPI volume / calendar-year population", **common),
            CanonicalRecord(date=observation_date, indicator="average_upi_transaction_value", value=average_value, unit="INR", method="Monthly UPI value / monthly UPI volume", **common),
            CanonicalRecord(date=observation_date, indicator="upi_value_pct_gdp", value=value_pct_gdp, unit="percent", method="Trailing 12-month UPI value / calendar-year nominal GDP * 100", **common),
        ))
    return output
