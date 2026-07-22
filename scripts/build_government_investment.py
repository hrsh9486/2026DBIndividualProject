"""Build central-government CapEx vintages and execution measures."""

from __future__ import annotations

import argparse
import logging

from builders import DatedSeriesDefinition, build_dated_multi_series_payload
from config import PROCESSED_DATA_DIR
from config.focused_indicators import get_focused_bundle
from exporters import publish_json
from extractors import RbiHandbookExtractor, UnionBudgetExtractor
from transforms.government_investment import (
    build_government_investment_records,
    parse_nominal_gdp_by_fiscal_year,
)
from validators import validate_dated_payload_quality, validate_records


LOGGER = logging.getLogger(__name__)


def build_payload(snapshots, gdp_response=None):
    bundle = get_focused_bundle("government_investment")
    nominal_gdp = parse_nominal_gdp_by_fiscal_year(gdp_response) if gdp_response else {}
    records = build_government_investment_records(
        snapshots,
        nominal_gdp_by_fiscal_year=nominal_gdp,
    )
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
        "name": f"Union Budget {snapshot.edition_start_year}-{str(snapshot.edition_start_year + 1)[-2:]}",
        "url": snapshot.source_url,
        "retrieved_at": snapshot.retrieved_at,
    } for snapshot in snapshots)
    if gdp_response:
        sources += ({
            "name": gdp_response.table_label,
            "url": gdp_response.source_url,
            "retrieved_at": gdp_response.retrieved_at,
        },)
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="GOVERNMENT_INVESTMENT_CAPEX_EXECUTION",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=sources,
        methodology="Each fiscal year's original BE, later RE and eventual actual are retained from separate Union Budget vintages; execution is actual divided by original BE.",
        note=bundle.limitation if gdp_response else f"Partial bundle: CapEx/GDP awaits a matching MoSPI nominal-GDP series. {bundle.limitation}",
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=(
            *(("actual_capex_pct_gdp",) if gdp_response else ()),
            "actual_capex_pct_total_expenditure",
            "capex_execution_ratio",
            "capex_budget_estimate",
            "capex_revised_estimate",
            "capex_actual",
        ),
        bounds={
            "actual_capex_pct_gdp": (0, None),
            "actual_capex_pct_total_expenditure": (0, 100),
            "capex_execution_ratio": (0, None),
            "capex_budget_estimate": (0, None),
            "capex_revised_estimate": (0, None),
            "capex_actual": (0, None),
        },
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-edition", type=int, default=2018)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    snapshots = UnionBudgetExtractor().fetch_expenditure_snapshots(args.start_edition)
    gdp_response = RbiHandbookExtractor().fetch_table(1)
    payload = build_payload(snapshots, gdp_response)
    output = PROCESSED_DATA_DIR / "government-investment" / "capex-and-execution.json"
    publish_json(payload, output, "dated_multi_series.schema.json")
    LOGGER.info("Published government investment bundle to %s", output)


if __name__ == "__main__":
    main()
