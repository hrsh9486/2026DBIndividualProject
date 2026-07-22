"""Build private fixed-investment ratios and lagged public-CapEx context."""

from __future__ import annotations

import json
import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors.national_accounts import NationalAccountsExtractor
from transforms.private_investment import build_lagged_public_capex_records, build_private_investment_records
from validators import validate_dated_payload_quality, validate_payload, validate_records


LOGGER = logging.getLogger(__name__)
GOVERNMENT_ARTIFACT = PROCESSED_DATA_DIR / "government-investment" / "capex-and-execution.json"


def build_payload(response, government_payload):
    bundle = get_focused_bundle("private_investment")
    records = build_private_investment_records(response)
    records.extend(build_lagged_public_capex_records(government_payload))
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
        indicator_code="PRIVATE_INVESTMENT_CROWDING_IN",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=({
            "name": "MoSPI new-series GDP estimates — Statement 7.1B",
            "url": response.source_url,
            "retrieved_at": response.retrieved_at,
        }, {
            "name": "Validated government investment artifact",
        }),
        methodology="Private corporate means private non-financial plus private financial corporations under the 2022-23 national-accounts base. The public-CapEx series is shifted forward one fiscal year.",
        note=f"Partial bundle: RBI OBICUS capacity utilisation is not yet ingested. {bundle.limitation}",
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=("private_corporate_gfcf_pct_gdp", "private_share_total_gfcf", "public_capex_lagged"),
        bounds={
            "private_corporate_gfcf_pct_gdp": (0, 100),
            "private_share_total_gfcf": (0, 100),
            "public_capex_lagged": (0, 100),
        },
    )
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not GOVERNMENT_ARTIFACT.is_file():
        raise FileNotFoundError("Build government investment before private investment")
    with GOVERNMENT_ARTIFACT.open(encoding="utf-8") as artifact_file:
        government_payload = json.load(artifact_file)
    validate_payload(government_payload, "dated_multi_series.schema.json")
    response = NationalAccountsExtractor().fetch()
    payload = build_payload(response, government_payload)
    output = PROCESSED_DATA_DIR / "private-investment" / "investment-and-capacity.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published private investment bundle to %s", output)


if __name__ == "__main__":
    main()
