"""Add the focused research programme to the static frontend catalogue.

Existing non-focused sections and assets are preserved until their removal is
explicitly approved. Focused bundles without a promoted artifact are exposed
as planned work rather than as empty live datasets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import PROJECT_ROOT
from config.focused_indicators import FOCUSED_BUNDLES, FocusedSeriesSpec
from exporters import write_json_atomic
from validators import validate_payload


CATALOGUE_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "catalogue.json"
FRONTEND_SCHEMA_DIR = PROJECT_ROOT / "frontend" / "public" / "data" / "schemas"


def _slug(value: str) -> str:
    return value.replace("_", "-")


def _value_format(series: FocusedSeriesSpec) -> dict:
    if series.unit in {"percent", "percentage_points"}:
        return {"style": "percent", "scale": 1, "decimals": 1}
    if series.unit == "INR":
        return {"style": "currency", "scale": 1, "decimals": 0, "currency": "INR"}
    if series.unit == "INR_crore":
        return {"style": "number", "scale": 1, "decimals": 0, "prefix": "₹", "suffix": " cr"}
    if series.unit == "index":
        return {"style": "index", "scale": 1, "decimals": 1}
    if series.unit == "ratio":
        return {"style": "ratio", "scale": 1, "decimals": 2}
    return {"style": "number", "scale": 1, "decimals": 2}


def _stale_after_days(frequency: str) -> int:
    return {"monthly": 45, "annual": 450, "mixed": 120}.get(frequency, 120)


def _artifact_availability(path: Path, bundle) -> str:
    if not path.is_file():
        return "planned"
    try:
        with path.open(encoding="utf-8") as artifact_file:
            artifact = json.load(artifact_file)
        series = artifact["series"]
        complete = all(
            any(observation.get("value") is not None for observation in series[spec.key]["values"])
            for spec in bundle.series
        )
    except (KeyError, TypeError, json.JSONDecodeError):
        return "partial"
    return "active" if complete else "partial"


def _section(bundle, *, order: int, asset_id: str) -> dict:
    indicators = []
    zero_line_series = {
        "gst_growth_gap",
        "primary_balance_pct_gdp",
        "reer_deviation_pct",
        "current_account_pct_gdp",
        "non_oil_export_growth",
        "dii_net_flow",
        "fpi_net_flow",
        "dii_rolling_12m",
        "fpi_rolling_12m",
    }
    for series in bundle.series:
        indicators.append({
            "id": _slug(series.key),
            "title": series.label,
            "summary": series.definition,
            "default_view": "main",
            "views": [{
                "id": "main",
                "label": "Time series",
                "asset_id": asset_id,
                "presentation": {
                    "component": "multi-series-line",
                    "chart_type": "line",
                    "x_axis": "date",
                    "default_visible": [series.key],
                    "value_format": _value_format(series),
                    "controls": {
                        "date_range": True,
                        "entity_toggle": False,
                        "series_toggle": False,
                    },
                    "zero_line": series.key in zero_line_series,
                    "show_source": True,
                    "show_methodology": True,
                },
                "note": series.limitation,
            }],
        })
    return {
        "id": _slug(bundle.key),
        "label": bundle.label,
        "order": order,
        "indicators": indicators,
    }


def build_catalogue(catalogue: dict, *, public_data_dir: Path) -> dict:
    """Return a focused catalogue while retaining unrelated legacy entries."""
    focused_ids = {_slug(key) for key in FOCUSED_BUNDLES}
    existing_sections = [
        section for section in catalogue.get("sections", [])
        if section.get("id") not in focused_ids
    ]
    for section in existing_sections:
        if section.get("order", 0) <= len(FOCUSED_BUNDLES):
            section["order"] += len(FOCUSED_BUNDLES)

    focused_sections = []
    for order, bundle in enumerate(FOCUSED_BUNDLES.values(), start=1):
        asset_id = _slug(bundle.key)
        promoted = public_data_dir / bundle.output_path
        availability = _artifact_availability(promoted, bundle)
        catalogue.setdefault("assets", {})[asset_id] = {
            "data_path": f"/data/{bundle.output_path}",
            "schema_path": "/data/schemas/dated_multi_series.schema.json",
            "schema": "dated_multi_series",
            "expected_frequency": bundle.frequency,
            "stale_after_days": _stale_after_days(bundle.frequency),
            "cache_strategy": "revalidate",
            "version": datetime.now(timezone.utc).date().isoformat(),
            "availability": availability,
            "description": bundle.research_question,
        }
        focused_sections.append(_section(bundle, order=order, asset_id=asset_id))

    catalogue["sections"] = focused_sections + existing_sections
    catalogue["generated_at"] = datetime.now(timezone.utc).isoformat()
    catalogue["roadmap_total"] = sum(len(section["indicators"]) for section in catalogue["sections"])
    return catalogue


def main() -> None:
    with CATALOGUE_PATH.open(encoding="utf-8") as catalogue_file:
        catalogue = json.load(catalogue_file)
    payload = build_catalogue(catalogue, public_data_dir=CATALOGUE_PATH.parent)
    validate_payload(payload, "catalogue.schema.json", schema_dir=FRONTEND_SCHEMA_DIR)
    write_json_atomic(payload, CATALOGUE_PATH)
    print(f"updated {CATALOGUE_PATH} with {len(FOCUSED_BUNDLES)} focused lenses")


if __name__ == "__main__":
    main()
