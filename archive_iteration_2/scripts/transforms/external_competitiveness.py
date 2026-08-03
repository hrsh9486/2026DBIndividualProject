"""Transform RBI Handbook tables into external-competitiveness measures."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from statistics import fmean
from typing import Iterable

from extractors.rbi_handbook import RbiHandbookResponse
from models import CanonicalRecord, ObservationStatus


_MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _retrieved(response: RbiHandbookResponse) -> datetime:
    return datetime.fromisoformat(response.retrieved_at)


def _status_for_calendar_year(year: int) -> ObservationStatus:
    return ObservationStatus.PROVISIONAL if year >= 2024 else ObservationStatus.ACTUAL


def _status_for_fiscal_year(start_year: int) -> ObservationStatus:
    if start_year >= 2024:
        return ObservationStatus.PROVISIONAL
    if start_year == 2023:
        return ObservationStatus.REVISED
    return ObservationStatus.ACTUAL


def parse_reer_records(response: RbiHandbookResponse) -> list[CanonicalRecord]:
    """Parse the RBI 40-currency trade-weighted REER monthly table."""
    levels: dict[date, float] = {}
    for sheet in response.sheets:
        years: list[int | None] = [None, None]
        for row in sheet.rows:
            year_values = [value for value in row if isinstance(value, int) and 1900 <= value <= 2100]
            if year_values:
                years[0] = year_values[0]
                if len(year_values) > 1:
                    years[1] = year_values[1]
                continue
            for block, offset in enumerate((0, 5)):
                if len(row) <= offset:
                    continue
                first = row[offset]
                if not isinstance(first, str) or years[block] is None:
                    continue
                month = _MONTHS.get(first.lower())
                value_index = offset + 2
                if month and len(row) > value_index and isinstance(row[value_index], (int, float)):
                    levels[_month_end(years[block], month)] = float(row[value_index])

    ordered = sorted(levels.items())
    output: list[CanonicalRecord] = []
    for index, (observation_date, value) in enumerate(ordered):
        common = {
            "date": observation_date,
            "entity": "IND",
            "frequency": "monthly",
            "source": "RBI Handbook of Statistics on the Indian Economy, 40-currency basket",
            "status": _status_for_calendar_year(observation_date.year),
            "source_url": response.source_url,
            "retrieved_at": _retrieved(response),
        }
        output.append(CanonicalRecord(
            indicator="reer_index",
            value=value,
            unit="index",
            **common,
        ))
        window = [item[1] for item in ordered[index - 59:index + 1]] if index >= 59 else []
        deviation = (value / fmean(window) - 1) * 100 if len(window) == 60 else None
        output.append(CanonicalRecord(
            indicator="reer_deviation_pct",
            value=deviation,
            unit="percent",
            is_derived=True,
            method="(REER / trailing 60-month arithmetic mean - 1) * 100",
            **common,
        ))
    return output


def parse_non_oil_export_growth_records(response: RbiHandbookResponse) -> list[CanonicalRecord]:
    """Parse monthly non-oil exports and calculate exact-month year-on-year growth."""
    levels: dict[date, tuple[float, int]] = {}
    for sheet in response.sheets:
        fiscal_years: list[int | None] = [None, None]
        for row in sheet.rows:
            for block, offset in enumerate((0, 5)):
                if len(row) <= offset:
                    continue
                first = row[offset]
                if isinstance(first, str) and first[:4].isdigit() and "-" in first:
                    fiscal_years[block] = int(first[:4])
                    continue
                if not isinstance(first, str) or fiscal_years[block] is None:
                    continue
                month = _MONTHS.get(first.lower())
                value_index = offset + 2
                if month and len(row) > value_index and isinstance(row[value_index], (int, float)):
                    start_year = fiscal_years[block]
                    calendar_year = start_year if month >= 4 else start_year + 1
                    levels[_month_end(calendar_year, month)] = (float(row[value_index]), start_year)

    records: list[CanonicalRecord] = []
    for observation_date, (value, fiscal_start) in sorted(levels.items()):
        prior_date = _month_end(observation_date.year - 1, observation_date.month)
        prior = levels.get(prior_date)
        if prior is None or prior[0] == 0:
            continue
        records.append(CanonicalRecord(
            date=observation_date,
            entity="IND",
            indicator="non_oil_export_growth",
            value=(value / prior[0] - 1) * 100,
            unit="percent",
            frequency="monthly",
            source="RBI Handbook; Directorate General of Commercial Intelligence and Statistics",
            status=_status_for_fiscal_year(fiscal_start),
            is_derived=True,
            method="Year-on-year growth in monthly non-oil merchandise exports in US dollars",
            source_url=response.source_url,
            retrieved_at=_retrieved(response),
        ))
    return records


def _quarter_end(label: str) -> date:
    year_match = label.rsplit(" ", 1)
    if len(year_match) != 2 or not year_match[1].isdigit():
        raise ValueError(f"Unexpected RBI quarter label: {label}")
    year = int(year_match[1])
    start_month = _MONTHS[label.split("-", 1)[0].lower()]
    end_month = {4: 6, 7: 9, 10: 12, 1: 3}[start_month]
    return _month_end(year, end_month)


def parse_current_account_values(response: RbiHandbookResponse) -> dict[date, float]:
    """Return quarterly current-account balances in INR crore."""
    values: dict[date, float] = {}
    for sheet in response.sheets:
        header = next((row for row in sheet.rows if row and row[0] == "Item/Year"), None)
        merchandise = next((row for row in sheet.rows if row and row[0] == "1. Merchandise"), None)
        invisibles = next((row for row in sheet.rows if row and str(row[0]).startswith("2. Invisibles")), None)
        if header is None or merchandise is None or invisibles is None:
            continue
        for quarter_index, label in enumerate(header[1:5]):
            net_index = 3 + quarter_index * 3
            if not isinstance(label, str):
                continue
            merchandise_net = merchandise[net_index]
            invisibles_net = invisibles[net_index]
            if isinstance(merchandise_net, (int, float)) and isinstance(invisibles_net, (int, float)):
                values[_quarter_end(label)] = float(merchandise_net + invisibles_net)
    return values


def parse_quarterly_gdp_values(response: RbiHandbookResponse) -> dict[date, float]:
    """Return quarterly nominal GDP in INR crore."""
    values: dict[date, float] = {}
    for sheet in response.sheets:
        header_index = next(
            (index for index, row in enumerate(sheet.rows) if row and str(row[0]).startswith("Item / Year")),
            None,
        )
        gdp = next((row for row in sheet.rows if row and row[0] == "9. Gross Domestic Product"), None)
        if header_index is None or gdp is None:
            continue
        years = [value for value in sheet.rows[header_index][1:] if isinstance(value, str)]
        for year_index, fiscal_label in enumerate(years):
            start_year = int(fiscal_label[:4])
            dates = (
                date(start_year, 6, 30),
                date(start_year, 9, 30),
                date(start_year, 12, 31),
                date(start_year + 1, 3, 31),
            )
            for quarter_index, observation_date in enumerate(dates):
                value_index = 1 + year_index * 4 + quarter_index
                if value_index < len(gdp) and isinstance(gdp[value_index], (int, float)):
                    values[observation_date] = float(gdp[value_index])
    return values


def build_current_account_pct_gdp_records(
    bop_response: RbiHandbookResponse,
    gdp_response: RbiHandbookResponse,
) -> list[CanonicalRecord]:
    current_account = parse_current_account_values(bop_response)
    gdp = parse_quarterly_gdp_values(gdp_response)
    records: list[CanonicalRecord] = []
    for observation_date in sorted(current_account.keys() & gdp.keys()):
        denominator = gdp[observation_date]
        records.append(CanonicalRecord(
            date=observation_date,
            entity="IND",
            indicator="current_account_pct_gdp",
            value=current_account[observation_date] / denominator * 100 if denominator else None,
            unit="percent",
            frequency="quarterly",
            source="RBI Handbook quarterly balance of payments and nominal GDP",
            status=_status_for_calendar_year(observation_date.year),
            is_derived=True,
            method="Quarterly current-account balance in INR crore / quarterly nominal GDP in INR crore * 100",
            source_url=bop_response.source_url,
            retrieved_at=_retrieved(bop_response),
        ))
    return records


def build_external_competitiveness_records(
    reer_response: RbiHandbookResponse,
    exports_response: RbiHandbookResponse,
    bop_response: RbiHandbookResponse,
    gdp_response: RbiHandbookResponse,
) -> list[CanonicalRecord]:
    records: list[CanonicalRecord] = []
    records.extend(parse_reer_records(reer_response))
    records.extend(parse_non_oil_export_growth_records(exports_response))
    records.extend(build_current_account_pct_gdp_records(bop_response, gdp_response))
    return records
