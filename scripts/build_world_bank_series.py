"""Build schema-validated annual country-comparison artifacts."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from builders import build_annual_country_payload
from config import COUNTRY_CODE, PEER_CODES, PROCESSED_DATA_DIR, START_YEAR
from config.indicators import Contract, Source, get_indicator, indicators_for
from exporters import publish_json
from extractors import WorldBankExtractor, WorldBankResponse
from helper import clean_float
from models import CanonicalRecord
from validators import validate_records


LOGGER = logging.getLogger(__name__)


def normalize_response(
    response: WorldBankResponse,
    *,
    entity: str,
    indicator_key: str,
    unit: str,
) -> list[CanonicalRecord]:
    """Parse a raw World Bank response into canonical annual records."""
    rows = response.payload[1] if len(response.payload) > 1 and response.payload[1] else []
    records = []
    for row in rows:
        year = row.get("date")
        if year is None:
            continue
        records.append(
            CanonicalRecord(
                date=date(int(year), 12, 31),
                entity=entity,
                indicator=indicator_key,
                value=clean_float(row.get("value"), None),
                unit=unit,
                frequency="annual",
                source="World Bank Indicators API",
            )
        )
    return records


def run_indicator(
    indicator_key: str,
    *,
    extractor: WorldBankExtractor | None = None,
    start_year: int = START_YEAR,
    end_year: int | None = None,
):
    spec = get_indicator(indicator_key)
    if spec.source is not Source.WORLD_BANK:
        raise ValueError(f"{indicator_key} is not a World Bank indicator")
    end_year = end_year or date.today().year
    extractor = extractor or WorldBankExtractor()
    records: list[CanonicalRecord] = []
    for entity in [COUNTRY_CODE, *PEER_CODES]:
        response = extractor.fetch(entity, spec.source_id, start_year, end_year)
        entity_records = normalize_response(
            response,
            entity=entity,
            indicator_key=spec.key,
            unit=spec.unit,
        )
        LOGGER.info("%s/%s: normalized %d rows", spec.key, entity, len(entity_records))
        records.extend(entity_records)

    checked = validate_records(records, expected_frequency=spec.frequency)
    payload = build_annual_country_payload(
        spec,
        checked,
        country=COUNTRY_CODE,
        peers=PEER_CODES,
        start_year=start_year,
        end_year=end_year,
    )
    output_path = PROCESSED_DATA_DIR / spec.output_path
    published = publish_json(payload, output_path, Contract.ANNUAL_COUNTRY_SERIES.value)
    LOGGER.info("%s: published %d canonical rows to %s", spec.key, len(checked), published)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("indicators", nargs="*", help="Registry keys; defaults to every World Bank indicator")
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    keys = args.indicators or [spec.key for spec in indicators_for(Source.WORLD_BANK)]
    failures = []
    for key in keys:
        try:
            run_indicator(key, start_year=args.start_year, end_year=args.end_year)
        except Exception as exc:  # isolate failures by source job
            LOGGER.error("%s failed: %s", key, exc)
            failures.append(key)
    if failures:
        raise SystemExit(f"Failed indicator jobs: {', '.join(failures)}")


if __name__ == "__main__":
    main()
