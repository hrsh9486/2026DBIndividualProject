"""Provider-neutral models for statistical evidence publications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Mapping


class EvidenceClass(str, Enum):
    DESCRIPTIVE = "descriptive"
    ASSOCIATIONAL = "associational"
    EVENT_STUDY = "event_study"
    CAUSAL = "causal"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    MIXED = "mixed"
    DESCRIPTIVE_ONLY = "descriptive_only"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED_DIAGNOSTICS = "failed_diagnostics"


class EvidenceGrade(str, Enum):
    NOT_ASSESSED = "not_assessed"
    DESCRIPTIVE = "descriptive"
    LIMITED = "limited"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(frozen=True, slots=True)
class Estimate:
    term: str
    value: float
    unit: str
    is_focal: bool = False
    standard_error: float | None = None
    confidence_level: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    p_value: float | None = None
    adjusted_p_value: float | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    key: str
    value: float | bool | str | None
    threshold: float | None
    passed: bool | None
    interpretation: str


@dataclass(frozen=True, slots=True)
class RobustnessResult:
    specification: str
    status: EvidenceStatus
    focal_estimate: Estimate | None
    sample_size: int
    note: str


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    eligible: bool
    required_observations: int
    available_observations: int
    reason: str
    checks: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    analysis_key: str
    status: EvidenceStatus
    grade: EvidenceGrade
    sample_size: int
    start_date: date | None
    end_date: date | None
    estimates: tuple[Estimate, ...] = ()
    diagnostics: tuple[DiagnosticResult, ...] = ()
    robustness: tuple[RobustnessResult, ...] = ()
    practical_interpretation: str = ""
    limitation: str = ""
    exclusion_summary: Mapping[str, int] = field(default_factory=dict)
    eligibility: EligibilityResult | None = None


@dataclass(frozen=True, slots=True)
class SourceAsset:
    path: str
    contract: str
    sha256: str
    generated_at: str
    start_date: date
    end_date: date
