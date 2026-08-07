"""Build the shared dated multi-series output contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, Mapping, Sequence

from models import CanonicalRecord
from models.capex_metrics import MetricSource
from config.capex_structural import CapexStructuralBundle


@dataclass(frozen=True, slots=True)
class DatedSeriesDefinition:
    key: str
    label: str
    entity: str
    unit: str
    is_derived: bool = False
    methodology: str | None = None
    source_note: str | None = None


def structural_definition(
    bundle: CapexStructuralBundle,
    key: str,
) -> DatedSeriesDefinition:
    """Convert one registered structural metric definition to output metadata."""
    for spec in bundle.series:
        if spec.key == key:
            return DatedSeriesDefinition(
                key=spec.key,
                label=spec.label,
                entity="IND",
                unit=spec.unit,
                is_derived=spec.is_derived,
                methodology=spec.transformation,
                source_note=spec.limitation,
            )
    raise KeyError(f"Structural bundle {bundle.key!r} has no series {key!r}")


def structural_definitions(
    bundle: CapexStructuralBundle,
    keys: tuple[str, ...],
) -> tuple[DatedSeriesDefinition, ...]:
    """Return registered definitions in the final output's explicit order."""
    return tuple(structural_definition(bundle, key) for key in keys)


def metric_source_rows(
    sources: tuple[MetricSource, ...],
) -> tuple[dict[str, str], ...]:
    """Convert typed provenance to the final JSON metadata contract."""
    rows = []
    for source in sources:
        row = {"name": source.name}
        if source.url is not None:
            row["url"] = source.url
        if source.retrieved_at is not None:
            row["retrieved_at"] = source.retrieved_at
        rows.append(row)
    return tuple(rows)


def select_metric_records(
    records: tuple[CanonicalRecord, ...],
    keys: tuple[str, ...],
    start_date: date,
) -> tuple[CanonicalRecord, ...]:
    """Select typed records for one final artifact without constructing JSON."""
    return tuple(
        record for record in records
        if record.indicator in keys and record.date >= start_date
    )


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
    indexed_records = [
        (record.date, record.indicator, record.entity, index, record)
        for index, record in enumerate(records)
    ]
    materialized = [item[4] for item in sorted(indexed_records)]
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
