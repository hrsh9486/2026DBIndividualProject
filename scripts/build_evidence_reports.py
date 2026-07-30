"""Estimate, validate and optionally promote the frozen evidence reports."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import platform
from pathlib import Path
import subprocess
import sys

from analysis.estimation import estimate_registered_evidence
from builders import build_evidence_report
from config import PROCESSED_DATA_DIR, PROJECT_ROOT
from config.evidence_specs import (
    EVIDENCE_OUTPUT_PATHS,
    EVIDENCE_SPECS,
    evidence_specs_for_lens,
)
from exporters import publish_evidence_report
from promote_processed_data import promote_artifact
from validators import validate_evidence_report


_VERSIONED_CODE_PATHS = (
    PROJECT_ROOT / "scripts" / "analysis",
    PROJECT_ROOT / "scripts" / "builders" / "evidence_report.py",
    PROJECT_ROOT / "scripts" / "config" / "evidence_specs.py",
    PROJECT_ROOT / "scripts" / "models" / "evidence.py",
    PROJECT_ROOT / "scripts" / "validators" / "evidence.py",
    PROJECT_ROOT / "scripts" / "build_evidence_reports.py",
    PROJECT_ROOT / "docs" / "decisions" / "0001-evidence-policy.md",
    PROJECT_ROOT / "docs" / "decisions" / "0002-evidence-estimation-policy.md",
    PROJECT_ROOT / "docs" / "decisions" / "0003-fiscal-exceptional-period-indicator.md",
    PROJECT_ROOT / "docs" / "decisions" / "0004-fiscal-exclusion-robustness-design.md",
)


def _versioned_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for path in _VERSIONED_CODE_PATHS:
        if path.is_dir():
            files.extend(sorted(path.glob("*.py")))
        else:
            files.append(path)
    return tuple(files)


def code_version() -> str:
    digest = hashlib.sha256()
    for path in _versioned_files():
        relative = path.relative_to(PROJECT_ROOT)
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        head = "no-git-head"
    return f"{head}+evidence.sha256.{digest.hexdigest()}"


def software_versions() -> dict[str, str]:
    return {
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "python": platform.python_version(),
        "scipy": version("scipy"),
        "statsmodels": version("statsmodels"),
    }


def build_reports() -> dict[str, dict]:
    prepared, results = estimate_registered_evidence()
    prepared_by_key = {item.spec.key: item for item in prepared}
    result_by_key = {item.analysis_key: item for item in results}
    reports: dict[str, dict] = {}
    lens_keys = tuple(dict.fromkeys(spec.lens_key for spec in EVIDENCE_SPECS.values()))
    for lens_key in lens_keys:
        specs = evidence_specs_for_lens(lens_key)
        source_by_path = {}
        for spec in specs:
            for source in prepared_by_key[spec.key].source_assets:
                existing = source_by_path.setdefault(source.path, source)
                if existing != source:
                    raise ValueError(
                        f"Source provenance differs within {lens_key}: {source.path}"
                    )
        reports[lens_key] = build_evidence_report(
            lens_key,
            tuple(result_by_key[spec.key] for spec in specs),
            source_assets=tuple(source_by_path.values()),
            code_version=code_version(),
            software_versions=software_versions(),
        )
    for report in reports.values():
        validate_evidence_report(report)
    return reports


def publish_reports(*, promote: bool = False) -> dict[str, Path]:
    reports = build_reports()
    destinations: dict[str, Path] = {}
    for lens_key, report in reports.items():
        relative_path = EVIDENCE_OUTPUT_PATHS[lens_key]
        destinations[lens_key] = publish_evidence_report(
            report,
            PROCESSED_DATA_DIR / relative_path,
        )
    if promote:
        for lens_key in reports:
            promote_artifact(EVIDENCE_OUTPUT_PATHS[lens_key])
        subprocess.run(
            [sys.executable, "scripts/sync_focused_catalogue.py"],
            cwd=PROJECT_ROOT,
            check=True,
        )
    return destinations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Also atomically promote validated reports to frontend/public/data.",
    )
    args = parser.parse_args()
    destinations = publish_reports(promote=args.promote)
    for lens_key, destination in sorted(destinations.items()):
        print(f"wrote {lens_key}: {destination}")


if __name__ == "__main__":
    main()
