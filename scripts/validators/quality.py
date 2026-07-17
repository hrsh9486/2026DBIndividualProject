"""Quality checks applied to canonical records before export."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

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
