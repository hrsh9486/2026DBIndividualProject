"""Typed calculated metrics passed between CapEx transformation stages."""

from __future__ import annotations

from dataclasses import dataclass

from models.canonical import CanonicalRecord


@dataclass(frozen=True, slots=True)
class MetricSource:
    name: str
    url: str | None = None
    retrieved_at: str | None = None


@dataclass(frozen=True, slots=True)
class GovernmentMetrics:
    records: tuple[CanonicalRecord, ...]
    sources: tuple[MetricSource, ...]


@dataclass(frozen=True, slots=True)
class PrivateMetrics:
    records: tuple[CanonicalRecord, ...]
    sources: tuple[MetricSource, ...]


@dataclass(frozen=True, slots=True)
class FiscalMetrics:
    records: tuple[CanonicalRecord, ...]
    sources: tuple[MetricSource, ...]
