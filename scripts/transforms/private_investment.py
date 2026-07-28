"""Private fixed-investment ratios and public-CapEx comparison records."""

from __future__ import annotations

from datetime import date, datetime

from extractors.national_accounts import NationalAccountsResponse
from extractors.rbi_obicus import ObicusResponse
from models import CanonicalRecord, FiscalPeriod, ObservationStatus


def build_private_investment_records(response: NationalAccountsResponse) -> list[CanonicalRecord]:
    records: list[CanonicalRecord] = []
    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    for observation in response.observations:
        period = FiscalPeriod(observation.fiscal_start_year)
        common = {
            "date": period.end_date,
            "entity": "IND",
            "unit": "percent",
            "frequency": "annual",
            "source": "MoSPI new-series national accounts, Statement 7.1B",
            "status": ObservationStatus.REVISED,
            "period_label": period.label,
            "is_derived": True,
            "source_url": response.source_url,
            "retrieved_at": retrieved_at,
            "period_start": period.start_date,
            "period_end": period.end_date,
        }
        records.extend((
            CanonicalRecord(
                indicator="private_corporate_gfcf_pct_gdp",
                value=observation.private_corporate_gfcf_crore / observation.nominal_gdp_crore * 100,
                method="Private non-financial plus private financial corporation GFCF / nominal GDP * 100",
                **common,
            ),
            CanonicalRecord(
                indicator="private_share_total_gfcf",
                value=observation.private_corporate_gfcf_crore / observation.total_gfcf_crore * 100,
                method="Private non-financial plus private financial corporation GFCF / total GFCF * 100",
                **common,
            ),
        ))
    return records


def build_lagged_public_capex_records(government_payload: dict) -> list[CanonicalRecord]:
    records: list[CanonicalRecord] = []
    values = government_payload["series"]["actual_capex_pct_gdp"]["values"]
    for item in values:
        source_date = date.fromisoformat(item["date"])
        period = FiscalPeriod(source_date.year)
        records.append(CanonicalRecord(
            date=period.end_date,
            entity="IND",
            indicator="public_capex_lagged",
            value=item.get("value"),
            unit="percent",
            frequency="annual",
            source="Derived from government-investment/capex-and-execution.json",
            status=ObservationStatus(item.get("status", "actual")),
            period_label=period.label,
            is_derived=True,
            method="Actual central-government CapEx/GDP shifted forward by one fiscal year",
            period_start=period.start_date,
            period_end=period.end_date,
        ))
    return records


def build_capacity_utilisation_records(response: ObicusResponse) -> list[CanonicalRecord]:
    """Map RBI OBICUS' unadjusted aggregate CU to fiscal-quarter end dates."""
    quarter_dates = {
        1: lambda year: (date(year, 4, 1), date(year, 6, 30)),
        2: lambda year: (date(year, 7, 1), date(year, 9, 30)),
        3: lambda year: (date(year, 10, 1), date(year, 12, 31)),
        4: lambda year: (date(year + 1, 1, 1), date(year + 1, 3, 31)),
    }
    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    records: list[CanonicalRecord] = []
    for observation in response.observations:
        period_start, period_end = quarter_dates[observation.quarter](observation.fiscal_start_year)
        fiscal_period = FiscalPeriod(observation.fiscal_start_year)
        records.append(CanonicalRecord(
            date=period_end,
            entity="IND",
            indicator="manufacturing_capacity_utilisation",
            value=observation.capacity_utilisation,
            unit="percent",
            frequency="quarterly",
            source="RBI Order Books, Inventories and Capacity Utilisation Survey (OBICUS)",
            status=ObservationStatus.PROVISIONAL,
            period_label=f"Q{observation.quarter}:{fiscal_period.label}",
            is_derived=False,
            method="Published unadjusted aggregate manufacturing capacity utilisation",
            source_url=response.source_url,
            retrieved_at=retrieved_at,
            period_start=period_start,
            period_end=period_end,
        ))
    return records
