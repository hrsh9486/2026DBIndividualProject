"""Print registered pre-estimation samples, exclusions and eligibility as JSON."""

from __future__ import annotations

import json

from analysis import prepare_registered_analysis
from config.evidence_specs import EVIDENCE_SPECS, SPECIFICATION_REGISTRY_VERSION


def build_readiness_snapshot() -> dict:
    analyses = []
    for analysis_key in EVIDENCE_SPECS:
        prepared = prepare_registered_analysis(analysis_key)
        analyses.append({
            "analysis_key": analysis_key,
            "lens_key": prepared.spec.lens_key,
            "sample": {
                "n": len(prepared.sample.rows),
                "start_date": (
                    prepared.sample.start_date.isoformat()
                    if prepared.sample.start_date
                    else None
                ),
                "end_date": (
                    prepared.sample.end_date.isoformat()
                    if prepared.sample.end_date
                    else None
                ),
                "excluded": dict(prepared.sample.excluded),
            },
            "eligibility": {
                "eligible": prepared.eligibility.eligible,
                "required_observations": prepared.eligibility.required_observations,
                "reason": prepared.eligibility.reason,
                "checks": dict(prepared.eligibility.checks),
            },
            "source_assets": [
                {
                    "path": asset.path,
                    "sha256": asset.sha256,
                    "generated_at": asset.generated_at,
                }
                for asset in prepared.source_assets
            ],
        })
    return {
        "specification_registry_version": SPECIFICATION_REGISTRY_VERSION,
        "analyses": analyses,
    }


def main() -> None:
    print(json.dumps(build_readiness_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
