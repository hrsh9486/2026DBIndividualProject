"""Validate and non-destructively promote processed artifacts to the frontend."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from config import PROCESSED_DATA_DIR, PROJECT_ROOT
from config.evidence_specs import EVIDENCE_OUTPUT_PATHS
from config.capex_analysis import OUTPUTS as CAPEX_OUTPUTS
from config.focused_indicators import FOCUSED_BUNDLES
from config.indicators import Contract, INDICATORS
from exporters import write_json_atomic
from validators import validate_evidence_report, validate_payload


FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"


@dataclass(frozen=True, slots=True)
class PromotionRoute:
    contract: Contract
    public_path: Path


PUBLIC_PATHS = {
    "real_effective_exchange_rate": "currency/reer-world-bank.json",
    "central_government_debt_pct_gdp": "macro/central-government-debt.json",
    "urban_population_pct": "workforce/urban-population.json",
    "labour_force_participation": "workforce/lfpr.json",
    "female_to_male_lfpr_ratio": "workforce/lfpr-gender-ratio.json",
    "working_age_share_pct": "workforce/working-age-share.json",
    "adult_literacy_rate": "education/adult-literacy.json",
    "secondary_enrolment": "education/secondary-enrolment.json",
    "tertiary_enrolment": "education/tertiary-enrolment.json",
    "secondary_education_expenditure": "education/secondary-education-spending.json",
    "medium_high_tech_exports": "trade/technology-exports.json",
    "fdi_net_inflows_pct_gdp": "trade/fdi-inflows.json",
}


def artifact_routes() -> dict[Path, PromotionRoute]:
    """Map registered processed paths to stable browser-facing paths."""
    routes = {
        Path(spec.output_path): PromotionRoute(spec.contract, Path(PUBLIC_PATHS[spec.key]))
        for spec in INDICATORS.values()
        if spec.key in PUBLIC_PATHS
    }
    routes.update({
        Path(spec.output_path): PromotionRoute(spec.contract, Path(spec.output_path))
        for spec in FOCUSED_BUNDLES.values()
    })
    routes.update({
        Path(path): PromotionRoute(Contract.EVIDENCE_REPORT, Path(path))
        for path in EVIDENCE_OUTPUT_PATHS.values()
    })
    routes[Path("equity/market_performance.json")] = PromotionRoute(
        Contract.MARKET_PERFORMANCE,
        Path("equities/market-performance.json"),
    )
    for key in ("execution", "correlations", "private", "fiscal", "corporate"):
        routes[Path(CAPEX_OUTPUTS[key])] = PromotionRoute(
            Contract.DATED_MULTI_SERIES, Path(CAPEX_OUTPUTS[key]),
        )
    routes[Path(CAPEX_OUTPUTS["sectors"])] = PromotionRoute(
        Contract.MARKET_PERFORMANCE, Path(CAPEX_OUTPUTS["sectors"]),
    )
    routes[Path(CAPEX_OUTPUTS["summary"])] = PromotionRoute(
        Contract.CAPEX_ANALYSIS_SUMMARY, Path(CAPEX_OUTPUTS["summary"]),
    )
    return routes


def promote_artifact(
    relative_path: str | Path,
    *,
    processed_root: str | Path = PROCESSED_DATA_DIR,
    frontend_root: str | Path = FRONTEND_DATA_DIR,
) -> Path:
    """Validate one registered artifact and atomically copy it to the frontend."""
    relative_path = Path(relative_path)
    route = artifact_routes().get(relative_path)
    if route is None:
        raise ValueError(f"No registered output contract for {relative_path}")

    source = Path(processed_root) / relative_path
    if not source.is_file():
        raise FileNotFoundError(f"Processed artifact does not exist: {source}")
    with source.open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if route.contract is Contract.EVIDENCE_REPORT:
        validate_evidence_report(payload)
    else:
        validate_payload(payload, route.contract.value)
    destination = Path(frontend_root) / route.public_path
    write_json_atomic(payload, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifacts",
        nargs="*",
        help="Paths relative to data/processed; defaults to all existing registered artifacts",
    )
    args = parser.parse_args()

    routes = artifact_routes()
    requested = [Path(path) for path in args.artifacts]
    artifacts = requested or [
        path for path in routes
        if (PROCESSED_DATA_DIR / path).is_file()
    ]
    if not artifacts:
        raise SystemExit("No processed artifacts found to promote")

    failures = []
    for artifact in artifacts:
        try:
            destination = promote_artifact(artifact)
            print(f"promoted {artifact} -> {destination}")
        except Exception as exc:
            print(f"FAILED {artifact}: {exc}")
            failures.append(str(artifact))
    if failures:
        raise SystemExit(f"Failed promotions: {', '.join(failures)}")


if __name__ == "__main__":
    main()
