"""Build debt-stock, debt-service and primary-balance fiscal indicators."""

from __future__ import annotations

import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors import RbiHandbookExtractor
from transforms.fiscal_capacity import build_fiscal_capacity_records
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)
DEBT_TABLE = 239
FISCAL_TABLE = 236


def build_payload(debt_response, fiscal_response):
    bundle = get_focused_bundle("fiscal_capacity")
    records = build_fiscal_capacity_records(debt_response, fiscal_response)
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
    sources = tuple({
        "name": response.table_label,
        "url": response.source_url,
        "retrieved_at": response.retrieved_at,
    } for response in (debt_response, fiscal_response))
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="FISCAL_CAPACITY_DEBT_SUSTAINABILITY",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=sources,
        methodology="Debt uses RBI adjusted combined Centre-and-State liabilities. Interest ratios divide consistent percentage-of-GDP components; primary balance is the negative of the reported gross primary deficit.",
        note=bundle.limitation,
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=tuple(spec.key for spec in bundle.series),
        bounds={
            "general_government_debt_pct_gdp": (0, None),
            "interest_payments_pct_revenue": (0, None),
            "interest_payments_pct_expenditure": (0, 100),
            "central_government_debt_pct_gdp": (0, None),
        },
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    extractor = RbiHandbookExtractor()
    debt_response = extractor.fetch_table(DEBT_TABLE)
    fiscal_response = extractor.fetch_table(FISCAL_TABLE)
    payload = build_payload(debt_response, fiscal_response)
    output = PROCESSED_DATA_DIR / "fiscal-capacity" / "debt-and-interest-burden.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published fiscal capacity bundle to %s", output)


if __name__ == "__main__":
    main()
