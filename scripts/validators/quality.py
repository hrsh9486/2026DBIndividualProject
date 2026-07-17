"""Quality checks applied to canonical records before export."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from models import CanonicalRecord


class DataQualityError(ValueError):
    """Raised when canonical data fails a production quality gate."""


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
