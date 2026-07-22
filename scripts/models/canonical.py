"""Provider-neutral records that retain source provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class ObservationStatus(str, Enum):
    ACTUAL = "actual"
    PROVISIONAL = "provisional"
    REVISED = "revised"
    ESTIMATE = "estimate"
    BUDGET = "budget"


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    """An Indian fiscal year represented by its inclusive date range."""

    start_year: int

    @property
    def label(self) -> str:
        return f"FY{self.start_year}-{str(self.start_year + 1)[-2:]}"

    @property
    def start_date(self) -> date:
        return date(self.start_year, 4, 1)

    @property
    def end_date(self) -> date:
        return date(self.start_year + 1, 3, 31)


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
    source_url: str | None = None
    retrieved_at: datetime | None = None
    vintage: str | None = None
    period_start: date | None = None
    period_end: date | None = None
