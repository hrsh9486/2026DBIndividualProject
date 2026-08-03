"""Build the annual India-versus-peer JSON contract."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from config.indicators import IndicatorSpec
from models import CanonicalRecord


def _year_values(
    records: Iterable[CanonicalRecord],
    entity: str,
    start_year: int,
    end_year: int,
) -> list[dict[str, int | float | None]]:
    values = {record.date.year: record.value for record in records if record.entity == entity}
    return [{"year": year, "value": values.get(year)} for year in range(start_year, end_year + 1)]


def build_annual_country_payload(
    spec: IndicatorSpec,
    records: Iterable[CanonicalRecord],
    *,
    country: str,
    peers: list[str],
    start_year: int,
    end_year: int,
) -> dict:
    materialized = list(records)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "World Bank Indicators API",
        "country": country,
        "peers": peers,
        "start_year": start_year,
        "end_year": end_year,
        "indicator_code": spec.source_id,
        "label": spec.label,
        "unit": spec.unit,
        "frequency": spec.frequency,
        "is_derived": spec.is_derived,
    }
    if spec.methodology:
        metadata["methodology"] = spec.methodology
    if spec.note:
        metadata["note"] = spec.note

    return {
        "metadata": metadata,
        "india": _year_values(materialized, country, start_year, end_year),
        "peers": {
            peer: _year_values(materialized, peer, start_year, end_year)
            for peer in peers
        },
    }
