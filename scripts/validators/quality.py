"""Quality checks applied to canonical records before export."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import math

from models import CanonicalRecord


class DataQualityError(ValueError):
    """Raised when canonical data fails a production quality gate."""


def validate_dated_rows(
    rows: Iterable[dict],
    *,
    required_series: Iterable[str] = (),
    minimum_observations: int = 2,
) -> list[dict]:
    """Reject short, duplicate, or incomplete chart-ready dated data."""
    materialized = list(rows)
    if len(materialized) < minimum_observations:
        raise DataQualityError(
            f"Expected at least {minimum_observations} dated observations; found {len(materialized)}"
        )
    dates = [row.get("date") for row in materialized]
    duplicates = [date for date, count in Counter(dates).items() if date is not None and count > 1]
    if None in dates:
        raise DataQualityError("Every dated observation must contain a date")
    if duplicates:
        raise DataQualityError(f"Duplicate observation dates: {duplicates[:5]}")
    missing = [key for key in required_series if not any(row.get(key) is not None for row in materialized)]
    if missing:
        raise DataQualityError(f"Required series contain no observations: {', '.join(missing)}")
    return materialized


def validate_correlation(value: float | None) -> float | None:
    """Require correlations to be null or inside the mathematical range."""
    if value is not None and not -1 <= value <= 1:
        raise DataQualityError(f"Correlation must be between -1 and 1; found {value}")
    return value


def validate_records(
    records: Iterable[CanonicalRecord],
    *,
    allow_empty: bool = False,
    expected_frequency: str | None = None,
) -> list[CanonicalRecord]:
    """Reject empty, duplicate, or frequency-drifted canonical data."""
    materialized = list(records)
    if not materialized and not allow_empty:
        raise DataQualityError("Source returned no canonical records")

    keys = [(record.entity, record.indicator, record.date) for record in materialized]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise DataQualityError(f"Duplicate entity/indicator/date records: {duplicates[:5]}")

    if expected_frequency:
        drift = sorted({record.frequency for record in materialized if record.frequency != expected_frequency})
        if drift:
            raise DataQualityError(
                f"Expected frequency {expected_frequency!r}; found {', '.join(drift)}"
            )
    return materialized


def validate_dated_payload_quality(
    payload: dict,
    *,
    required_non_empty: Iterable[str] = (),
    bounds: dict[str, tuple[float | None, float | None]] | None = None,
) -> None:
    """Check ordering, duplicate periods, finite values, coverage and bounds."""
    all_dates: list[str] = []
    series = payload.get("series", {})
    for key in required_non_empty:
        values = series.get(key, {}).get("values", [])
        if not values or not any(observation.get("value") is not None for observation in values):
            raise DataQualityError(f"Required output series contains no observations: {key}")
    for key, item in series.items():
        values = item.get("values", [])
        dates = [observation.get("date") for observation in values]
        if dates != sorted(dates):
            raise DataQualityError(f"Series {key} is not ordered by date")
        duplicates = [period for period, count in Counter(dates).items() if count > 1]
        if duplicates:
            raise DataQualityError(f"Series {key} contains duplicate dates: {duplicates[:5]}")
        for observation in values:
            value = observation.get("value")
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise DataQualityError(f"Series {key} contains a non-finite value")
            lower, upper = (bounds or {}).get(key, (None, None))
            if value is not None and lower is not None and value < lower:
                raise DataQualityError(f"Series {key} value {value} is below {lower}")
            if value is not None and upper is not None and value > upper:
                raise DataQualityError(f"Series {key} value {value} is above {upper}")
        all_dates.extend(date_value for date_value in dates if date_value)
    if not all_dates:
        raise DataQualityError("Dated payload contains no observations")
    metadata = payload.get("metadata", {})
    if metadata.get("start_date") != min(all_dates) or metadata.get("end_date") != max(all_dates):
        raise DataQualityError("Metadata date range does not match observation coverage")
