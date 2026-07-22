"""Build the first focused bundle: UPI adoption and digital integration.

The initial publication intentionally leaves the GST series empty until the
historical GST/MoSPI join has an independently tested extractor.
"""

from __future__ import annotations

import logging
from datetime import datetime

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors.npci import NpciExtractor
from extractors.world_bank import WorldBankExtractor
from transforms import build_upi_canonical_records
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)
POPULATION_CODE = "SP.POP.TOTL"
NOMINAL_GDP_INR_CODE = "NY.GDP.MKTP.CN"


def _world_bank_year_values(response) -> dict[int, float]:
    rows = response.payload[1] if len(response.payload) > 1 and response.payload[1] else []
    return {
        int(row["date"]): float(row["value"])
        for row in rows
        if row.get("date") is not None and row.get("value") is not None
    }


def build_payload(upi_response, population_by_year, nominal_gdp_by_year):
    bundle = get_focused_bundle("digital_integration")
    retrieved_at = datetime.fromisoformat(upi_response.retrieved_at)
    records = build_upi_canonical_records(
        upi_response.records,
        population_by_year=population_by_year,
        nominal_gdp_inr_by_year=nominal_gdp_by_year,
        source_url=upi_response.source_url,
        retrieved_at=retrieved_at,
    )
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
        indicator_code="DIGITAL_INTEGRATION_UPI_TAX",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=(
            {"name": "National Payments Corporation of India", "url": upi_response.source_url, "retrieved_at": upi_response.retrieved_at},
            {"name": "World Bank Indicators API"},
        ),
        methodology="UPI measures use official monthly volume/value with annual population and GDP denominators; no missing observations are interpolated.",
        note=f"Partial bundle: GST evidence is pending. {bundle.limitation}",
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=("upi_transactions_per_capita", "average_upi_transaction_value", "upi_value_pct_gdp"),
        bounds={
            "upi_transactions_per_capita": (0, None),
            "average_upi_transaction_value": (0, None),
            "upi_value_pct_gdp": (0, None),
        },
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    upi_response = NpciExtractor().fetch_upi_monthly()
    start_year = min(record.year for record in upi_response.records)
    end_year = max(record.year for record in upi_response.records)
    world_bank = WorldBankExtractor()
    population = _world_bank_year_values(world_bank.fetch("IND", POPULATION_CODE, start_year, end_year))
    nominal_gdp = _world_bank_year_values(world_bank.fetch("IND", NOMINAL_GDP_INR_CODE, start_year, end_year))
    payload = build_payload(upi_response, population, nominal_gdp)
    output = PROCESSED_DATA_DIR / "digital-integration" / "upi-and-tax-capacity.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published digital integration bundle to %s", output)


if __name__ == "__main__":
    main()
