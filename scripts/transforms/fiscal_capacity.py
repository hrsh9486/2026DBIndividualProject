"""Transform RBI public-finance tables into fiscal-capacity measures."""

from __future__ import annotations

import re
from datetime import datetime

from extractors.rbi_handbook import RbiHandbookResponse
from models import CanonicalRecord, FiscalPeriod, ObservationStatus


_FISCAL_YEAR = re.compile(r"^(\d{4})-\d{2}$")


def _start_year(value) -> int | None:
    if not isinstance(value, str):
        return None
    match = _FISCAL_YEAR.match(value)
    return int(match.group(1)) if match else None


def _flow_status(start_year: int) -> ObservationStatus:
    if start_year >= 2025:
        return ObservationStatus.BUDGET
    if start_year == 2024:
        return ObservationStatus.REVISED
    return ObservationStatus.ACTUAL


def _debt_status(start_year: int) -> ObservationStatus:
    if start_year >= 2024:
        return ObservationStatus.BUDGET
    if start_year == 2023:
        return ObservationStatus.REVISED
    return ObservationStatus.ACTUAL


def parse_debt_records(response: RbiHandbookResponse) -> list[CanonicalRecord]:
    """Parse central and adjusted combined-government liabilities as % GDP."""
    records: list[CanonicalRecord] = []
    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    for sheet in response.sheets:
        for row in sheet.rows:
            start_year = _start_year(row[0] if row else None)
            if start_year is None or len(row) < 7:
                continue
            central, combined = row[3], row[6]
            if not isinstance(central, (int, float)) or not isinstance(combined, (int, float)):
                continue
            period = FiscalPeriod(start_year)
            common = {
                "date": period.end_date,
                "entity": "IND",
                "unit": "percent",
                "frequency": "annual",
                "source": "RBI Handbook — Select Debt Indicators of Central and State Governments",
                "status": _debt_status(start_year),
                "period_label": period.label,
                "source_url": response.source_url,
                "retrieved_at": retrieved_at,
                "period_start": period.start_date,
                "period_end": period.end_date,
            }
            records.extend((
                CanonicalRecord(
                    indicator="general_government_debt_pct_gdp",
                    value=float(combined),
                    **common,
                ),
                CanonicalRecord(
                    indicator="central_government_debt_pct_gdp",
                    value=float(central),
                    **common,
                ),
            ))
    return records


def parse_fiscal_burden_records(response: RbiHandbookResponse) -> list[CanonicalRecord]:
    """Parse primary balance and derive interest burden from % GDP components."""
    primary_deficit: dict[int, float] = {}
    revenue_receipts: dict[int, float] = {}
    interest_payments: dict[int, float] = {}
    total_expenditure: dict[int, float] = {}
    for sheet in response.sheets:
        header_text = " ".join(str(value) for row in sheet.rows[:4] for value in row if value is not None)
        for row in sheet.rows:
            start_year = _start_year(row[0] if row else None)
            if start_year is None:
                continue
            if "Gross Primary Deficit" in header_text and len(row) > 3 and isinstance(row[3], (int, float)):
                primary_deficit[start_year] = float(row[3])
            elif "Revenue Receipts" in header_text and len(row) > 5 and isinstance(row[5], (int, float)):
                revenue_receipts[start_year] = float(row[5])
            elif "Interest Payments" in header_text and len(row) > 7:
                if isinstance(row[2], (int, float)):
                    interest_payments[start_year] = float(row[2])
                if isinstance(row[7], (int, float)):
                    total_expenditure[start_year] = float(row[7])

    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    records: list[CanonicalRecord] = []
    for start_year in sorted(set(primary_deficit) | set(interest_payments)):
        period = FiscalPeriod(start_year)
        common = {
            "date": period.end_date,
            "entity": "IND",
            "unit": "percent",
            "frequency": "annual",
            "source": "RBI Handbook — Select Fiscal Indicators of the Central Government",
            "status": _flow_status(start_year),
            "period_label": period.label,
            "source_url": response.source_url,
            "retrieved_at": retrieved_at,
            "period_start": period.start_date,
            "period_end": period.end_date,
        }
        if start_year in primary_deficit:
            records.append(CanonicalRecord(
                indicator="primary_balance_pct_gdp",
                value=-primary_deficit[start_year],
                is_derived=True,
                method="Negative of RBI gross primary deficit as a percentage of GDP",
                **common,
            ))
        interest = interest_payments.get(start_year)
        revenue = revenue_receipts.get(start_year)
        expenditure = total_expenditure.get(start_year)
        if interest is not None and revenue:
            records.append(CanonicalRecord(
                indicator="interest_payments_pct_revenue",
                value=interest / revenue * 100,
                is_derived=True,
                method="Interest payments % GDP / revenue receipts % GDP * 100",
                **common,
            ))
        if interest is not None and expenditure:
            records.append(CanonicalRecord(
                indicator="interest_payments_pct_expenditure",
                value=interest / expenditure * 100,
                is_derived=True,
                method="Interest payments % GDP / total expenditure % GDP * 100",
                **common,
            ))
    return records


def build_fiscal_capacity_records(
    debt_response: RbiHandbookResponse,
    fiscal_response: RbiHandbookResponse,
) -> list[CanonicalRecord]:
    return parse_debt_records(debt_response) + parse_fiscal_burden_records(fiscal_response)
