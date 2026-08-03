"""Validated loading of registered measurement series for evidence work."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from config import PROCESSED_DATA_DIR
from config.evidence_specs import SeriesInput
from config.focused_indicators import FOCUSED_BUNDLES, FocusedBundleSpec
from models import ObservationStatus, SourceAsset
from validators import validate_payload


@dataclass(frozen=True, slots=True)
class LoadedObservation:
    date: date
    value: float | None
    status: ObservationStatus
    period_label: str | None = None


@dataclass(frozen=True, slots=True)
class LoadedSeries:
    name: str
    asset_path: str
    series_key: str
    entity: str
    unit: str
    frequency: str
    artifact_sha256: str
    artifact_generated_at: str
    artifact_start_date: date
    artifact_end_date: date
    observations: tuple[LoadedObservation, ...]

    def source_asset(self, contract: str) -> SourceAsset:
        return SourceAsset(
            path=self.asset_path,
            contract=contract,
            sha256=self.artifact_sha256,
            generated_at=self.artifact_generated_at,
            start_date=self.artifact_start_date,
            end_date=self.artifact_end_date,
        )


def _bundle_for_path(path: str) -> FocusedBundleSpec:
    matches = [bundle for bundle in FOCUSED_BUNDLES.values() if bundle.output_path == path]
    if len(matches) != 1:
        raise ValueError(f"Evidence input path is not one registered focused artifact: {path}")
    return matches[0]


class RegisteredArtifactLoader:
    """Open only registered processed artifacts and retain observation provenance."""

    def __init__(self, *, processed_root: str | Path = PROCESSED_DATA_DIR) -> None:
        self.processed_root = Path(processed_root)

    def load(self, input_spec: SeriesInput) -> LoadedSeries:
        bundle = _bundle_for_path(input_spec.asset_path)
        registered_series = next(
            (item for item in bundle.series if item.key == input_spec.series_key),
            None,
        )
        if registered_series is None:
            raise ValueError(
                f"Series {input_spec.series_key} is not registered in {input_spec.asset_path}"
            )
        if (
            registered_series.unit != input_spec.expected_unit
            or registered_series.frequency != input_spec.expected_frequency
        ):
            raise ValueError(f"Evidence input declaration drifted: {input_spec.name}")

        artifact_path = self.processed_root / input_spec.asset_path
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Registered evidence input does not exist: {artifact_path}")
        artifact_bytes = artifact_path.read_bytes()
        payload = json.loads(artifact_bytes)
        validate_payload(payload, bundle.contract.value)

        try:
            metadata = payload["metadata"]
            series_payload = payload["series"][input_spec.series_key]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Evidence artifact lacks {input_spec.series_key}") from exc
        if series_payload["unit"] != input_spec.expected_unit:
            raise ValueError(f"Evidence artifact unit drifted: {input_spec.name}")
        if series_payload["entity"] != "IND":
            raise ValueError(f"Focused evidence input must use entity IND: {input_spec.name}")

        observations: list[LoadedObservation] = []
        seen_dates: set[date] = set()
        for item in series_payload["values"]:
            observation_date = date.fromisoformat(item["date"])
            if observation_date in seen_dates:
                raise ValueError(f"Duplicate evidence input date: {input_spec.name}/{observation_date}")
            seen_dates.add(observation_date)
            value = item.get("value")
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"Evidence input value is not numeric: {input_spec.name}")
                if not math.isfinite(value):
                    raise ValueError(f"Evidence input value is not finite: {input_spec.name}")
                value = float(value)
            observations.append(LoadedObservation(
                date=observation_date,
                value=value,
                status=ObservationStatus(item.get("status", "actual")),
                period_label=item.get("period_label"),
            ))
        observations.sort(key=lambda item: item.date)
        if not observations:
            raise ValueError(f"Evidence input series is empty: {input_spec.name}")

        artifact_start = date.fromisoformat(metadata["start_date"])
        artifact_end = date.fromisoformat(metadata["end_date"])
        if observations[0].date < artifact_start or observations[-1].date > artifact_end:
            raise ValueError(f"Evidence series lies outside artifact coverage: {input_spec.name}")
        datetime.fromisoformat(metadata["generated_at"])
        return LoadedSeries(
            name=input_spec.name,
            asset_path=input_spec.asset_path,
            series_key=input_spec.series_key,
            entity=series_payload["entity"],
            unit=series_payload["unit"],
            frequency=input_spec.expected_frequency,
            artifact_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            artifact_generated_at=metadata["generated_at"],
            artifact_start_date=artifact_start,
            artifact_end_date=artifact_end,
            observations=tuple(observations),
        )
