"""Build an accumulating NSE institutional-flow resilience bundle."""

from __future__ import annotations

import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors import NseInstitutionalFlowExtractor
from transforms.capital_resilience import build_capital_resilience_records
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)


def build_payload(response):
    bundle = get_focused_bundle("capital_resilience")
    records = build_capital_resilience_records(response)
    validate_records(records, expected_frequency="monthly")
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
        indicator_code="DOMESTIC_CAPITAL_BUFFER",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=({
            "name": "NSE FII/FPI and DII trading activity",
            "url": response.source_url,
            "retrieved_at": response.retrieved_at,
        },),
        methodology="Each run archives NSE's current provisional daily observation. Monthly sums, rolling 12-month flows and the DII offset ratio are calculated only from the accumulated official archive.",
        note="Partial accumulating bundle: NSE's public endpoint exposes today's provisional activity, not a historical daily download. Twelve-month measures remain null until twelve consecutive archived months exist. " + bundle.limitation,
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=("dii_net_flow", "fpi_net_flow"),
        bounds={"dii_offset_ratio": (0, None)},
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    response = NseInstitutionalFlowExtractor().fetch()
    payload = build_payload(response)
    output = PROCESSED_DATA_DIR / "capital-resilience" / "institutional-flows.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published capital-resilience bundle to %s", output)


if __name__ == "__main__":
    main()
