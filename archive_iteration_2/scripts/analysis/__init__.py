"""Reusable sample construction and eligibility infrastructure."""

from .alignment import AlignedRow, AlignedSample, align_registered_inputs
from .eligibility import evaluate_eligibility, insufficient_evidence_result
from .loader import LoadedObservation, LoadedSeries, RegisteredArtifactLoader
from .pipeline import PreparedAnalysis, prepare_registered_analysis

__all__ = [
    "AlignedRow",
    "AlignedSample",
    "LoadedObservation",
    "LoadedSeries",
    "PreparedAnalysis",
    "RegisteredArtifactLoader",
    "align_registered_inputs",
    "evaluate_eligibility",
    "insufficient_evidence_result",
    "prepare_registered_analysis",
]
