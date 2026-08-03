"""Synchronise browser-facing schemas from the authoritative backend copies."""

from __future__ import annotations

import shutil

from config import PROJECT_ROOT, SCHEMA_DIR


PUBLIC_SCHEMA_DIR = PROJECT_ROOT / "frontend" / "public" / "data" / "schemas"
PUBLIC_SCHEMAS = (
    "annual_country_series.schema.json",
    "dated_multi_series.schema.json",
    "event_study.schema.json",
    "evidence_report.schema.json",
    "market_performance.schema.json",
    "capex_analysis_summary.schema.json",
)


def sync_public_schemas() -> tuple[str, ...]:
    PUBLIC_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    updated: list[str] = []
    for name in PUBLIC_SCHEMAS:
        source = SCHEMA_DIR / name
        destination = PUBLIC_SCHEMA_DIR / name
        source_bytes = source.read_bytes()
        if not destination.exists() or destination.read_bytes() != source_bytes:
            shutil.copyfile(source, destination)
            updated.append(name)
    return tuple(updated)


def main() -> None:
    updated = sync_public_schemas()
    print(
        "schemas already synchronised"
        if not updated
        else "synchronised " + ", ".join(updated)
    )


if __name__ == "__main__":
    main()
