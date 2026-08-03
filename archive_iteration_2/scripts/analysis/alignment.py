"""Status-aware transformations, lags, aggregation and registered joins."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Mapping

from config.evidence_specs import (
    AlignmentStrategy,
    EvidenceSpec,
    SeriesInput,
    Transformation,
)
from models import ObservationStatus

from .loader import LoadedObservation, LoadedSeries


@dataclass(frozen=True, slots=True)
class _PreparedObservation:
    target_date: date
    source_date: date
    value: float
    status: ObservationStatus


@dataclass(frozen=True, slots=True)
class AlignedRow:
    date: date
    values: Mapping[str, float]
    statuses: Mapping[str, ObservationStatus]
    source_dates: Mapping[str, date]


@dataclass(frozen=True, slots=True)
class AlignedSample:
    rows: tuple[AlignedRow, ...]
    excluded: Mapping[str, int]
    input_observations: Mapping[str, int]

    @property
    def start_date(self) -> date | None:
        return self.rows[0].date if self.rows else None

    @property
    def end_date(self) -> date | None:
        return self.rows[-1].date if self.rows else None


def _period_index(observation_date: date, frequency: str) -> int:
    if frequency == "monthly":
        return observation_date.year * 12 + observation_date.month
    if frequency == "quarterly":
        quarter = (observation_date.month - 1) // 3 + 1
        return observation_date.year * 4 + quarter
    if frequency in {"annual", "fiscal_year", "academic_year"}:
        return observation_date.year
    raise ValueError(f"Unsupported evidence period frequency: {frequency}")


def _eligible_observations(
    input_spec: SeriesInput,
    loaded: LoadedSeries,
    *,
    analysis_start_date: date | None,
    excluded: Counter,
) -> list[LoadedObservation]:
    eligible: list[LoadedObservation] = []
    for observation in loaded.observations:
        if analysis_start_date and observation.date < analysis_start_date:
            excluded[f"{input_spec.name}:before_start"] += 1
        elif observation.status not in input_spec.allowed_statuses:
            excluded[f"{input_spec.name}:status"] += 1
        elif observation.value is None:
            excluded[f"{input_spec.name}:missing_value"] += 1
        elif (
            input_spec.transformation in {Transformation.LOG, Transformation.LOG_DIFFERENCE}
            and observation.value <= 0
        ):
            excluded[f"{input_spec.name}:nonpositive_log"] += 1
        else:
            eligible.append(observation)
    return eligible


def _transform(
    input_spec: SeriesInput,
    loaded: LoadedSeries,
    *,
    analysis_start_date: date | None,
    excluded: Counter,
) -> list[_PreparedObservation]:
    eligible = _eligible_observations(
        input_spec,
        loaded,
        analysis_start_date=analysis_start_date,
        excluded=excluded,
    )
    transformed: list[_PreparedObservation] = []
    by_index = {
        _period_index(item.date, loaded.frequency): item
        for item in eligible
    }
    for observation in eligible:
        period_index = _period_index(observation.date, loaded.frequency)
        value = float(observation.value)
        source_date = observation.date
        if input_spec.transformation in {Transformation.LOG, Transformation.LOG_DIFFERENCE}:
            value = math.log(value)
        if input_spec.transformation in {Transformation.DIFFERENCE, Transformation.LOG_DIFFERENCE}:
            previous = by_index.get(period_index - 1)
            if previous is None:
                excluded[f"{input_spec.name}:difference_unavailable"] += 1
                continue
            previous_value = float(previous.value)
            if input_spec.transformation is Transformation.LOG_DIFFERENCE:
                if previous_value <= 0:
                    excluded[f"{input_spec.name}:difference_unavailable"] += 1
                    continue
                previous_value = math.log(previous_value)
            value -= previous_value

        transformed.append(_PreparedObservation(
            target_date=observation.date,
            source_date=source_date,
            value=value,
            status=observation.status,
        ))

    if input_spec.lag_periods:
        all_dates_by_index = {
            _period_index(item.date, loaded.frequency): item.date
            for item in loaded.observations
        }
        lagged: list[_PreparedObservation] = []
        for item in transformed:
            source_index = _period_index(item.target_date, loaded.frequency)
            target_date = all_dates_by_index.get(source_index + input_spec.lag_periods)
            if target_date is None:
                excluded[f"{input_spec.name}:lag_unavailable"] += 1
                continue
            if target_date <= item.source_date:
                raise ValueError(f"Lag introduced future information: {input_spec.name}")
            lagged.append(_PreparedObservation(
                target_date=target_date,
                source_date=item.source_date,
                value=item.value,
                status=item.status,
            ))
        transformed = lagged
    return transformed


def _quarter_end(year: int, quarter: int) -> date:
    return {
        1: date(year, 3, 31),
        2: date(year, 6, 30),
        3: date(year, 9, 30),
        4: date(year, 12, 31),
    }[quarter]


def _quarter_key(observation_date: date) -> tuple[int, int]:
    return observation_date.year, (observation_date.month - 1) // 3 + 1


def _aggregate_monthly_to_quarter(
    observations: list[_PreparedObservation],
    strategy: AlignmentStrategy,
    *,
    input_name: str,
    excluded: Counter,
) -> list[_PreparedObservation]:
    grouped: dict[tuple[int, int], list[_PreparedObservation]] = defaultdict(list)
    for item in observations:
        grouped[_quarter_key(item.target_date)].append(item)
    output: list[_PreparedObservation] = []
    for (year, quarter), items in sorted(grouped.items()):
        month_count = len({_period_index(item.target_date, "monthly") for item in items})
        if month_count != 3:
            excluded[f"{input_name}:incomplete_quarter"] += 1
            continue
        ordered = sorted(items, key=lambda item: item.target_date)
        if strategy is AlignmentStrategy.MONTHLY_TO_QUARTERLY_MEAN:
            value = mean(item.value for item in ordered)
        elif strategy is AlignmentStrategy.MONTHLY_TO_QUARTERLY_SUM:
            value = sum(item.value for item in ordered)
        else:
            value = ordered[-1].value
        output.append(_PreparedObservation(
            target_date=_quarter_end(year, quarter),
            source_date=max(item.source_date for item in ordered),
            value=value,
            status=ordered[-1].status,
        ))
    return output


def _join_key(observation_date: date, strategy: AlignmentStrategy):
    if strategy in {
        AlignmentStrategy.EXACT_DATE_INNER_JOIN,
        AlignmentStrategy.LAG_THEN_INNER_JOIN,
    }:
        return observation_date
    if strategy is AlignmentStrategy.CALENDAR_YEAR_INNER_JOIN:
        return observation_date.year
    if strategy is AlignmentStrategy.FISCAL_YEAR_END_INNER_JOIN:
        if (observation_date.month, observation_date.day) != (3, 31):
            raise ValueError(f"Fiscal alignment received a non-fiscal-year-end date: {observation_date}")
        return observation_date.year
    if strategy is AlignmentStrategy.QUARTER_END_INNER_JOIN:
        if observation_date.month not in {3, 6, 9, 12}:
            raise ValueError(f"Quarter alignment received a non-quarter-end month: {observation_date}")
        return _quarter_key(observation_date)
    if strategy in {
        AlignmentStrategy.MONTHLY_TO_QUARTERLY_MEAN,
        AlignmentStrategy.MONTHLY_TO_QUARTERLY_END,
        AlignmentStrategy.MONTHLY_TO_QUARTERLY_SUM,
    }:
        return _quarter_key(observation_date)
    raise NotImplementedError(f"Alignment strategy is not implemented yet: {strategy.value}")


def _row_date(key, strategy: AlignmentStrategy) -> date:
    if isinstance(key, date):
        return key
    if strategy is AlignmentStrategy.CALENDAR_YEAR_INNER_JOIN:
        return date(key, 12, 31)
    if strategy is AlignmentStrategy.FISCAL_YEAR_END_INNER_JOIN:
        return date(key, 3, 31)
    if isinstance(key, tuple):
        return _quarter_end(*key)
    raise ValueError(f"Cannot construct aligned row date for {key!r}")


def align_registered_inputs(
    spec: EvidenceSpec,
    loaded_by_name: Mapping[str, LoadedSeries],
) -> AlignedSample:
    """Apply declared transformations/lags and construct a complete inner join."""
    expected_names = {item.name for item in spec.inputs}
    if set(loaded_by_name) != expected_names:
        raise ValueError(f"Loaded inputs do not match registered inputs for {spec.key}")
    excluded: Counter = Counter()
    prepared: dict[str, list[_PreparedObservation]] = {}
    for input_spec in spec.inputs:
        loaded = loaded_by_name[input_spec.name]
        items = _transform(
            input_spec,
            loaded,
            analysis_start_date=spec.analysis_start_date,
            excluded=excluded,
        )
        if (
            spec.alignment
            in {
                AlignmentStrategy.MONTHLY_TO_QUARTERLY_MEAN,
                AlignmentStrategy.MONTHLY_TO_QUARTERLY_END,
                AlignmentStrategy.MONTHLY_TO_QUARTERLY_SUM,
            }
            and loaded.frequency == "monthly"
        ):
            items = _aggregate_monthly_to_quarter(
                items,
                spec.alignment,
                input_name=input_spec.name,
                excluded=excluded,
            )
        prepared[input_spec.name] = items

    keyed: dict[str, dict[object, _PreparedObservation]] = {}
    for name, items in prepared.items():
        keyed[name] = {}
        for item in items:
            key = _join_key(item.target_date, spec.alignment)
            if key in keyed[name]:
                raise ValueError(f"Evidence alignment produced duplicate periods: {spec.key}/{name}")
            keyed[name][key] = item
    common_keys = set.intersection(*(set(items) for items in keyed.values())) if keyed else set()
    for name, items in keyed.items():
        excluded[f"{name}:alignment"] += len(set(items) - common_keys)

    rows: list[AlignedRow] = []
    for key in sorted(common_keys):
        observations = {name: items[key] for name, items in keyed.items()}
        rows.append(AlignedRow(
            date=_row_date(key, spec.alignment),
            values={name: item.value for name, item in observations.items()},
            statuses={name: item.status for name, item in observations.items()},
            source_dates={name: item.source_date for name, item in observations.items()},
        ))
    return AlignedSample(
        rows=tuple(rows),
        excluded={key: value for key, value in sorted(excluded.items()) if value},
        input_observations={
            name: len(loaded.observations)
            for name, loaded in loaded_by_name.items()
        },
    )
