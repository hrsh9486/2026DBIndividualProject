"""Validate and promote only the active CapEx artifacts to the frontend."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from config import PROCESSED_DATA_DIR, PROJECT_ROOT
from config.capex_analysis import OUTPUTS
from exporters import write_json_atomic
from validators import validate_payload


FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"


@dataclass(frozen=True, slots=True)
class PromotionRoute:
    schema_name: str
    public_path: Path


def artifact_routes() -> dict[Path, PromotionRoute]:
    routes: dict[Path, PromotionRoute] = {}
    for key, relative in OUTPUTS.items():
        schema = (
            "market_performance.schema.json" if key == "sectors"
            else "capex_analysis_summary.schema.json" if key == "summary"
            else "dated_multi_series.schema.json"
        )
        path = Path(relative)
        routes[path] = PromotionRoute(schema, path)
    return routes


def promote_artifact(
    relative_path: str | Path,
    *,
    processed_root: str | Path = PROCESSED_DATA_DIR,
    frontend_root: str | Path = FRONTEND_DATA_DIR,
) -> Path:
    """Revalidate one registered CapEx artifact before atomic promotion."""
    relative_path = Path(relative_path)
    route = artifact_routes().get(relative_path)
    if route is None:
        raise ValueError(f"No active CapEx output contract for {relative_path}")
    source = Path(processed_root) / relative_path
    if not source.is_file():
        raise FileNotFoundError(f"Processed artifact does not exist: {source}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_payload(payload, route.schema_name)
    destination = Path(frontend_root) / route.public_path
    write_json_atomic(payload, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifacts",
        nargs="*",
        help="CapEx paths relative to data/processed; defaults to every existing active output",
    )
    args = parser.parse_args()
    routes = artifact_routes()
    artifacts = [Path(path) for path in args.artifacts] or [
        path for path in routes if (PROCESSED_DATA_DIR / path).is_file()
    ]
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
