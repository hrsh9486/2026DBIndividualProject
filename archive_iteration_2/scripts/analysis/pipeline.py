"""Orchestrate registered loading, alignment and pre-estimation eligibility."""

from __future__ import annotations

from dataclasses import dataclass

from config.evidence_specs import EVIDENCE_SPECS, EvidenceSpec
from models import EligibilityResult, SourceAsset

from .alignment import AlignedSample, align_registered_inputs
from .eligibility import evaluate_eligibility
from .loader import RegisteredArtifactLoader


@dataclass(frozen=True, slots=True)
class PreparedAnalysis:
    spec: EvidenceSpec
    sample: AlignedSample
    eligibility: EligibilityResult
    source_assets: tuple[SourceAsset, ...]


def prepare_registered_analysis(
    analysis_key: str,
    *,
    loader: RegisteredArtifactLoader | None = None,
) -> PreparedAnalysis:
    """Prepare a registered sample without estimating or inspecting coefficients."""
    try:
        spec = EVIDENCE_SPECS[analysis_key]
    except KeyError as exc:
        raise KeyError(f"Unknown registered evidence analysis: {analysis_key}") from exc
    artifact_loader = loader or RegisteredArtifactLoader()
    loaded_by_name = {
        input_spec.name: artifact_loader.load(input_spec)
        for input_spec in spec.inputs
    }
    sample = align_registered_inputs(spec, loaded_by_name)
    eligibility = evaluate_eligibility(spec, sample)
    assets: dict[str, SourceAsset] = {}
    for input_spec in spec.inputs:
        loaded = loaded_by_name[input_spec.name]
        assets.setdefault(
            loaded.asset_path,
            loaded.source_asset("dated_multi_series"),
        )
    return PreparedAnalysis(
        spec=spec,
        sample=sample,
        eligibility=eligibility,
        source_assets=tuple(assets.values()),
    )
