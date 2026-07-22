"""Build the shared dated multi-series output contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

from models import CanonicalRecord


@dataclass(frozen=True, slots=True)
class DatedSeriesDefinition:
    key: str
    label: str
    entity: str
    unit: str
    is_derived: bool = False
    methodology: str | None = None
    source_note: str | None = None


def build_dated_multi_series_payload(
    records: Iterable[CanonicalRecord],
    definitions: Sequence[DatedSeriesDefinition],
    *,
    indicator_code: str,
    label: str,
    frequency: str,
    sources: Sequence[Mapping[str, str]],
    default_unit: str = "mixed",
    methodology: str | None = None,
    note: str | None = None,
) -> dict:
    """Build a deterministic payload without filling missing observations."""
    materialized = sorted(records, key=lambda record: (record.date, record.indicator, record.entity))
    if not materialized:
        raise ValueError("Cannot build a dated-series payload without records")
    definition_by_key = {definition.key: definition for definition in definitions}
    unknown = sorted({record.indicator for record in materialized} - definition_by_key.keys())
    if unknown:
        raise ValueError(f"Records have no series definition: {', '.join(unknown)}")

    series = {}
    for definition in definitions:
        values = []
        matching = [record for record in materialized if record.indicator == definition.key]
        for record in matching:
            value = {"date": record.date.isoformat(), "value": record.value, "status": record.status.value}
            if record.period_label:
                value["period_label"] = record.period_label
            values.append(value)
        item = {
            "label": definition.label,
            "entity": definition.entity,
            "unit": definition.unit,
            "is_derived": definition.is_derived,
            "values": values,
        }
        if definition.methodology:
            item["methodology"] = definition.methodology
        if definition.source_note:
            item["source_note"] = definition.source_note
        series[definition.key] = item

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": [dict(source) for source in sources],
        "frequency": frequency,
        "start_date": min(record.date for record in materialized).isoformat(),
        "end_date": max(record.date for record in materialized).isoformat(),
        "indicator_code": indicator_code,
        "label": label,
        "default_unit": default_unit,
        "series_order": [definition.key for definition in definitions],
        "is_derived": any(definition.is_derived for definition in definitions),
    }
    if methodology:
        metadata["methodology"] = methodology
    if note:
        metadata["note"] = note
    return {"metadata": metadata, "series": series}
