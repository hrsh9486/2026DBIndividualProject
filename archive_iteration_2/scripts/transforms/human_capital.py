"""Transform official AISHE and PLFS series into canonical records."""

from __future__ import annotations

from datetime import date, datetime

from extractors.human_capital import HumanCapitalSourceResponse
from models import CanonicalRecord, ObservationStatus


def _annual_records(
    response: HumanCapitalSourceResponse,
    *,
    indicator: str,
    source: str,
    period_kind: str,
) -> list[CanonicalRecord]:
    retrieved_at = datetime.fromisoformat(response.retrieved_at)
    records = []
    for item in response.values:
        if period_kind == "academic":
            observation_date = date(item.year + 1, 3, 31)
            period_label = f"AY{item.year}-{str(item.year + 1)[-2:]}"
            period_start = date(item.year, 4, 1)
        else:
            observation_date = date(item.year, 12, 31)
            period_label = str(item.year)
            period_start = date(item.year, 1, 1)
        records.append(CanonicalRecord(
            date=observation_date,
            entity="IND",
            indicator=indicator,
            value=item.value,
            unit="percent",
            frequency="annual",
            source=source,
            status=ObservationStatus.ACTUAL,
            period_label=period_label,
            source_url=response.source_url,
            retrieved_at=retrieved_at,
            period_start=period_start,
            period_end=observation_date,
        ))
    return records


def build_human_capital_records(
    ger: HumanCapitalSourceResponse,
    unemployment: HumanCapitalSourceResponse,
    salaried: HumanCapitalSourceResponse,
) -> list[CanonicalRecord]:
    records = _annual_records(
        ger,
        indicator="tertiary_ger",
        source="AISHE 2023-24, Table 47",
        period_kind="academic",
    )
    records.extend(_annual_records(
        unemployment,
        indicator="educated_unemployment",
        source="PLFS 2025, Statement 17",
        period_kind="calendar",
    ))
    records.extend(_annual_records(
        salaried,
        indicator="regular_salaried_employment_share",
        source="PLFS 2025, Statement 7",
        period_kind="calendar",
    ))
    return records
