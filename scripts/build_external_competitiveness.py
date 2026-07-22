"""Build RBI-sourced external competitiveness and resilience indicators."""

from __future__ import annotations

import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors import RbiHandbookExtractor
from transforms.external_competitiveness import build_external_competitiveness_records
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)
TABLES = {
    "reer": 206,
    "exports": 192,
    "bop_rupees": 195,
    "quarterly_gdp": 155,
}


def build_payload(responses):
    bundle = get_focused_bundle("external_competitiveness")
    records = build_external_competitiveness_records(
        responses["reer"],
        responses["exports"],
        responses["bop_rupees"],
        responses["quarterly_gdp"],
    )
    validate_records(records)
    definitions = tuple(
        DatedSeriesDefinition(
            key=spec.key,
            label=spec.label,
            entity="IND",
            unit=spec.unit,
            is_derived=spec.is_derived,
            methodology=spec.transformation,
            source_note=spec.limitation,
        )
        for spec in bundle.series
    )
    sources = tuple({
        "name": response.table_label,
        "url": response.source_url,
        "retrieved_at": response.retrieved_at,
    } for response in responses.values())
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="EXTERNAL_COMPETITIVENESS_RESILIENCE",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=sources,
        methodology="Official RBI monthly and quarterly tables; REER deviation uses a trailing 60-month arithmetic mean and export growth uses exact month-on-month-year matches.",
        note=bundle.limitation,
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=tuple(spec.key for spec in bundle.series),
        bounds={
            "reer_index": (0, None),
            "reer_deviation_pct": (-100, None),
            "current_account_pct_gdp": (-100, 100),
            "non_oil_export_growth": (-100, None),
        },
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    extractor = RbiHandbookExtractor()
    responses = {key: extractor.fetch_table(number) for key, number in TABLES.items()}
    payload = build_payload(responses)
    output = PROCESSED_DATA_DIR / "external-competitiveness" / "reer-and-current-account.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published external competitiveness bundle to %s", output)


if __name__ == "__main__":
    main()
