"""Run the seven focused India data jobs, promote them, and refresh the catalogue."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from config import PROJECT_ROOT
from config.focused_indicators import FOCUSED_BUNDLES


BUILD_ORDER = (
    ("digital_integration", "scripts/build_digital_integration.py"),
    ("government_investment", "scripts/build_government_investment.py"),
    ("private_investment", "scripts/build_private_investment.py"),
    ("fiscal_capacity", "scripts/build_fiscal_capacity.py"),
    ("external_competitiveness", "scripts/build_external_competitiveness.py"),
    ("human_capital", "scripts/build_human_capital.py"),
    ("capital_resilience", "scripts/build_capital_resilience.py"),
)


def _run(command: list[str], *, cwd=PROJECT_ROOT) -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundles",
        nargs="*",
        choices=tuple(key for key, _ in BUILD_ORDER),
        help="Optional bundle keys; defaults to all seven in dependency order.",
    )
    parser.add_argument(
        "--frontend-build",
        action="store_true",
        help="Also validate and compile the React frontend after promotion.",
    )
    args = parser.parse_args()
    requested = set(args.bundles) if args.bundles else {key for key, _ in BUILD_ORDER}

    for key, script in BUILD_ORDER:
        if key in requested:
            print(f"building {key}", flush=True)
            _run([sys.executable, script])

    artifacts = [
        FOCUSED_BUNDLES[key].output_path
        for key, _ in BUILD_ORDER
        if key in requested
    ]
    _run([sys.executable, "scripts/promote_processed_data.py", *artifacts])
    _run([sys.executable, "scripts/sync_focused_catalogue.py"])
    if args.frontend_build:
        _run(["npm", "run", "build"], cwd=PROJECT_ROOT / "frontend")


if __name__ == "__main__":
    main()
