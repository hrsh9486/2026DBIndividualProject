"""Run the complete CapEx ETL pipeline from source acquisition to published JSON."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from builders.capex_artifacts import CapexArtifacts, build_capex_artifacts
from config import PROJECT_ROOT
from config.capex_analysis import OUTPUTS, OUTPUT_SCHEMAS
from exporters import write_json_atomic
from extractors.capex_sources import acquire_capex_sources, load_landed_capex_sources
from validators import validate_payload


TARGET_CHOICES = (
    "all",
    *(f"output:{key}" for key in OUTPUTS),
)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    written_paths: tuple[Path, ...]
    processed_artifacts: int
    public_artifacts: int


def _require_complete_artifacts(artifacts: CapexArtifacts) -> None:
    output_keys = set(OUTPUTS)
    if set(artifacts.outputs) != output_keys:
        raise ValueError(
            f"CapEx artifact set mismatch: expected {sorted(output_keys)}, "
            f"received {sorted(artifacts.outputs)}"
        )


def _artifact_entries(artifacts: CapexArtifacts) -> tuple[tuple[Path, dict, str, bool], ...]:
    """Return every final payload; all final payloads have a public copy."""
    return tuple(
        (Path(relative), artifacts.outputs[key], OUTPUT_SCHEMAS[key], True)
        for key, relative in OUTPUTS.items()
    )


def _validate_all_artifacts(
    artifacts: CapexArtifacts,
) -> tuple[tuple[Path, dict, str, bool], ...]:
    """Reject an incomplete, schema-invalid or non-serialisable run before publication."""
    _require_complete_artifacts(artifacts)
    entries = _artifact_entries(artifacts)
    for _relative, payload, schema_name, _publish_public in entries:
        validate_payload(payload, schema_name)
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            default=str,
        )
    return entries


def _select_artifact_entries(
    entries: tuple[tuple[Path, dict, str, bool], ...],
    target: str,
) -> tuple[tuple[Path, dict, str, bool], ...]:
    """Select the validated artifacts that the Load step should write."""
    if target == "all":
        return entries
    if target.startswith("output:"):
        key = target.removeprefix("output:")
        relative = OUTPUTS.get(key)
    else:
        relative = None
    if relative is None:
        raise ValueError(
            f"Unknown pipeline target {target!r}; expected one of: {', '.join(TARGET_CHOICES)}"
        )
    selected = tuple(
        entry
        for entry in entries
        if entry[0] == Path(relative)
    )
    if len(selected) != 1:
        raise ValueError(f"Pipeline target {target!r} did not resolve to exactly one artifact")
    return selected


def _publish_artifacts(
    project_root: Path,
    entries: tuple[tuple[Path, dict, str, bool], ...],
) -> tuple[Path, ...]:
    """Write validated processed artifacts and their registered public copies."""
    processed_root = project_root / "data" / "processed"
    public_root = project_root / "frontend" / "public" / "data"
    written: list[Path] = []
    for relative, payload, _schema_name, publish_public in entries:
        written.append(write_json_atomic(payload, processed_root / relative))
        if publish_public:
            written.append(write_json_atomic(payload, public_root / relative))
    return tuple(written)


def _verify_written_artifacts(
    project_root: Path,
    entries: tuple[tuple[Path, dict, str, bool], ...],
) -> None:
    """Revalidate every written processed file and compare public copies when present."""
    processed_root = project_root / "data" / "processed"
    public_root = project_root / "frontend" / "public" / "data"
    for relative, _payload, schema_name, publish_public in entries:
        processed = processed_root / relative
        if not processed.is_file():
            raise FileNotFoundError(f"Processed artifact is missing: {relative}")
        validate_payload(
            json.loads(processed.read_text(encoding="utf-8")),
            schema_name,
        )
        if not publish_public:
            continue
        public = public_root / relative
        if not public.is_file():
            raise FileNotFoundError(f"Public artifact is missing: {relative}")
        processed_hash = hashlib.sha256(processed.read_bytes()).digest()
        public_hash = hashlib.sha256(public.read_bytes()).digest()
        if processed_hash != public_hash:
            raise ValueError(f"Processed/public content mismatch: {relative}")


def run_pipeline(
    *,
    project_root: str | Path = PROJECT_ROOT,
    start_edition: int = 2018,
    prices_json: str | Path | None = None,
    offline: bool = False,
    target: str = "all",
) -> PipelineResult:
    """Extract, transform, validate, publish and verify the complete CapEx product."""
    project_root = Path(project_root)
    if target not in TARGET_CHOICES:
        raise ValueError(
            f"Unknown pipeline target {target!r}; expected one of: {', '.join(TARGET_CHOICES)}"
        )
    raw_root = project_root / "data" / "raw"
    print("[1/5] EXTRACT: acquire or replay immutable raw sources", flush=True)
    if offline:
        sources = load_landed_capex_sources(
            raw_root,
            start_edition=start_edition,
        )
    else:
        sources = acquire_capex_sources(
            raw_root,
            start_edition=start_edition,
            prices_json=prices_json,
        )

    print("[2/5] TRANSFORM: calculate statistics and assemble all artifacts in memory", flush=True)
    artifacts = build_capex_artifacts(sources)

    print("[3/5] VALIDATE: check the complete 13-output artifact set", flush=True)
    entries = _validate_all_artifacts(artifacts)
    selected_entries = _select_artifact_entries(entries, target)

    print(f"[4/5] LOAD: write target {target!r} with one atomic replacement per file", flush=True)
    written_paths = _publish_artifacts(project_root, selected_entries)

    print("[5/5] VERIFY: revalidate written files and compare public copies", flush=True)
    _verify_written_artifacts(project_root, selected_entries)
    print("CapEx ETL pipeline published and verified.", flush=True)
    return PipelineResult(
        written_paths=written_paths,
        processed_artifacts=len(selected_entries),
        public_artifacts=sum(
            1 for _relative, _payload, _schema_name, publish_public in selected_entries
            if publish_public
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-edition", type=int, default=2018)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Replay the latest immutable files in data/raw instead of using the network.",
    )
    parser.add_argument(
        "--prices-json",
        type=Path,
        help="Use a landed price matrix instead of the live Nifty source.",
    )
    parser.add_argument(
        "--target",
        choices=TARGET_CHOICES,
        default="all",
        help=(
            "Choose which validated artifact to write; all sources and artifacts are still "
            "extracted, transformed and validated. Defaults to all."
        ),
    )
    args = parser.parse_args()
    if args.offline and args.prices_json:
        parser.error("--offline and --prices-json cannot be used together")
    run_pipeline(
        start_edition=args.start_edition,
        prices_json=args.prices_json,
        offline=args.offline,
        target=args.target,
    )


if __name__ == "__main__":
    main()
