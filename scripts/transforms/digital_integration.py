"""Deterministic digital-integration calculations."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Mapping, Sequence

from extractors.gst_revenue import GstRevenueResponse
from extractors.npci import UpiMonthlyRecord
from models import CanonicalRecord, FiscalPeriod, ObservationStatus


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


def _least_final_status(*statuses: ObservationStatus) -> ObservationStatus:
    order = {
        ObservationStatus.ACTUAL: 0,
        ObservationStatus.REVISED: 1,
        ObservationStatus.PROVISIONAL: 2,
        ObservationStatus.ESTIMATE: 3,
        ObservationStatus.BUDGET: 4,
    }
    return max(statuses, key=order.__getitem__)


def build_gst_growth_gap_records(
    response: GstRevenueResponse,
    *,
    nominal_gdp_by_fiscal_year: Mapping[int, tuple[float, ObservationStatus]],
) -> list[CanonicalRecord]:
    """Subtract fiscal-year nominal-GDP growth from gross-GST growth."""
    observations = {item.fiscal_start_year: item for item in response.observations}
    records: list[CanonicalRecord] = []
    for fiscal_year in sorted(observations):
        previous_year = fiscal_year - 1
        current = observations[fiscal_year]
        previous = observations.get(previous_year)
        current_gdp = nominal_gdp_by_fiscal_year.get(fiscal_year)
        previous_gdp = nominal_gdp_by_fiscal_year.get(previous_year)
        if previous is None or current_gdp is None or previous_gdp is None:
            continue
        if previous.gross_gst_crore <= 0 or current_gdp[0] <= 0 or previous_gdp[0] <= 0:
            raise ValueError("GST and nominal-GDP levels must be positive")
        gst_growth = (current.gross_gst_crore / previous.gross_gst_crore - 1) * 100
        nominal_gdp_growth = (current_gdp[0] / previous_gdp[0] - 1) * 100
        period = FiscalPeriod(fiscal_year)
        records.append(CanonicalRecord(
            date=period.end_date,
            entity="IND",
            indicator="gst_growth_gap",
            value=gst_growth - nominal_gdp_growth,
            unit="percentage_points",
            frequency="annual",
            source="GST Portal / Ministry of Finance; RBI Handbook (NSO nominal GDP)",
            status=_least_final_status(current.status, current_gdp[1]),
            period_label=period.label,
            is_derived=True,
            method="Gross GST revenue YoY growth minus fiscal-year nominal GDP YoY growth",
            source_url=current.source_url,
            retrieved_at=datetime.fromisoformat(current.retrieved_at),
            period_start=period.start_date,
            period_end=period.end_date,
        ))
    return records
