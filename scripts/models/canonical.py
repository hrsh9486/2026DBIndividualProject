"""Provider-neutral records that retain source provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ObservationStatus(str, Enum):
    ACTUAL = "actual"
    PROVISIONAL = "provisional"
    REVISED = "revised"
    ESTIMATE = "estimate"
    BUDGET = "budget"


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    date: date
    entity: str
    indicator: str
    value: float | None
    unit: str
    frequency: str
    source: str
    status: ObservationStatus = ObservationStatus.ACTUAL
    period_label: str | None = None
    is_derived: bool = False
    method: str | None = None
