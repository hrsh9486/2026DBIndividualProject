"""Extract typed annual observations from the tracked delivery reference source."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from config import REFERENCE_SOURCE_DIR
from models.capex_sources import (
    AnnualSourceDataset,
    AnnualSourceObservation,
    AnnualSourceSeries,
    DeliverySources,
    SourceReference,
)


REFERENCE_FILENAME = "capex_delivery_reference.json"
EXPECTED_SERIES = {
    "allocation": ("railways_budget_capex", "roads_budget_capex"),
    "delivery": (
        "national_highways_constructed_km",
        "railway_route_km_electrified",
    ),
    "production": ("capital_goods_iip",),
}
VALID_STATUSES = {"actual", "budget"}


def _read_references(rows: object, dataset_key: str) -> tuple[SourceReference, ...]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{dataset_key} must contain at least one source reference")
    references = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Invalid source reference in {dataset_key}")
        references.append(SourceReference(
            name=str(row["name"]),
            url=str(row["url"]),
            retrieved_at=str(row["retrieved_at"]),
        ))
    return tuple(references)


def _read_series(dataset_key: str, raw_series: object) -> tuple[AnnualSourceSeries, ...]:
    if not isinstance(raw_series, dict):
        raise ValueError(f"{dataset_key}.series must be an object")
    expected = EXPECTED_SERIES[dataset_key]
    if tuple(raw_series) != expected:
        raise ValueError(
            f"{dataset_key} series mismatch: expected {expected}, received {tuple(raw_series)}"
        )
    result = []
    for series_key in expected:
        raw_definition = raw_series[series_key]
        if not isinstance(raw_definition, dict):
            raise ValueError(f"Invalid series definition: {dataset_key}.{series_key}")
        status = str(raw_definition.get("status"))
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status for {dataset_key}.{series_key}: {status}")
        raw_observations = raw_definition.get("observations")
        if not isinstance(raw_observations, dict) or not raw_observations:
            raise ValueError(f"No observations for {dataset_key}.{series_key}")
        observations = []
        previous_period = ""
        for fiscal_period, raw_value in raw_observations.items():
            if fiscal_period <= previous_period:
                raise ValueError(f"Periods are not strictly increasing in {dataset_key}.{series_key}")
            try:
                start_year = int(fiscal_period[:4])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid fiscal period {fiscal_period!r}") from exc
            if fiscal_period != f"{start_year:04d}-{str(start_year + 1)[-2:]}":
                raise ValueError(f"Invalid fiscal period {fiscal_period!r}")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(f"Non-finite value in {dataset_key}.{series_key}")
            observations.append(AnnualSourceObservation(fiscal_period, value, status))
            previous_period = fiscal_period
        result.append(AnnualSourceSeries(series_key, tuple(observations)))
    return tuple(result)


def _read_dataset(payload: dict, dataset_key: str) -> AnnualSourceDataset:
    raw_dataset = payload.get(dataset_key)
    if not isinstance(raw_dataset, dict):
        raise ValueError(f"Missing source dataset {dataset_key!r}")
    return AnnualSourceDataset(
        key=dataset_key,
        references=_read_references(raw_dataset.get("references"), dataset_key),
        series=_read_series(dataset_key, raw_dataset.get("series")),
    )


def extract_delivery_sources(
    reference_path: str | Path = REFERENCE_SOURCE_DIR / REFERENCE_FILENAME,
) -> DeliverySources:
    """Parse and validate every manually transcribed annual source observation."""
    source = Path(reference_path)
    content = source.read_bytes()
    payload = json.loads(content)
    if set(payload) != set(EXPECTED_SERIES):
        raise ValueError(
            f"Reference dataset mismatch: expected {sorted(EXPECTED_SERIES)}, received {sorted(payload)}"
        )
    return DeliverySources(
        allocation=_read_dataset(payload, "allocation"),
        delivery=_read_dataset(payload, "delivery"),
        production=_read_dataset(payload, "production"),
        reference_path=source,
        checksum=hashlib.sha256(content).hexdigest(),
    )
