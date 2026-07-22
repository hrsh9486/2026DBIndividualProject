"""Build the education-to-employment human-capital lens."""

from __future__ import annotations

import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors import HumanCapitalExtractor
from transforms.human_capital import build_human_capital_records
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)


def build_payload(ger, unemployment, salaried):
    bundle = get_focused_bundle("human_capital")
    records = build_human_capital_records(ger, unemployment, salaried)
    validate_records(records, expected_frequency="annual")
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
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="HUMAN_CAPITAL_EMPLOYMENT_CONVERSION",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=({
            "name": "AISHE Final Report 2023-24 — Table 47",
            "url": ger.source_url,
            "retrieved_at": ger.retrieved_at,
        }, {
            "name": "PLFS Annual Report 2025 — Statements 7 and 17",
            "url": unemployment.source_url,
            "retrieved_at": unemployment.retrieved_at,
        }),
        methodology="AISHE reports academic-year tertiary GER for ages 18-23. PLFS reports calendar-year usual-status (ps+ss) measures for people aged 15+; the published educated-unemployment trend is secondary and above.",
        note=bundle.limitation,
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=tuple(spec.key for spec in bundle.series),
        bounds={spec.key: (0, 100) for spec in bundle.series},
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    extractor = HumanCapitalExtractor()
    ger = extractor.fetch_aishe_ger()
    unemployment, salaried = extractor.fetch_plfs()
    payload = build_payload(ger, unemployment, salaried)
    output = PROCESSED_DATA_DIR / "human-capital" / "education-and-employment.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published human-capital bundle to %s", output)


if __name__ == "__main__":
    main()
