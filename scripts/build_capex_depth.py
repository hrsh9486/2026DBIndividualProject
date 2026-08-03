"""Build the investment-quality, state-evaluation and crowding-in extensions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import PROCESSED_DATA_DIR
from config.capex_analysis import OUTPUTS
from exporters import publish_json
from extractors import RbiHandbookExtractor
from transforms.capex_depth import (
    build_crowding_in_payload,
    build_investment_quality_payload,
    build_state_capex_evaluation_payload,
)
from validators import validate_payload


LOGGER = logging.getLogger(__name__)


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_payload(payload, "dated_multi_series.schema.json")
    return payload


def build_depth_payloads(*, extractor: RbiHandbookExtractor | None = None) -> dict[str, dict]:
    extractor = extractor or RbiHandbookExtractor()
    project_status = extractor.fetch_publication(
        21841,
        table_number=35,
        table_label="RBI Handbook 2022-23, Table 35 — Implementation of Central Sector Projects",
    )
    project_cost = extractor.fetch_publication(
        21842,
        table_number=36,
        table_label="RBI Handbook 2022-23, Table 36 — Cost Overrun of Delayed Central Sector Projects",
    )
    current_gsdp = extractor.fetch_publication(
        23470,
        table_number=21,
        table_label="RBI Handbook of Statistics on Indian States, Table 21 — GSDP at Current Prices",
    )
    constant_gsdp = extractor.fetch_publication(
        23471,
        table_number=22,
        table_label="RBI Handbook of Statistics on Indian States, Table 22 — GSDP at Constant Prices",
    )
    capital_outlay = extractor.fetch_publication(
        23623,
        table_number=174,
        table_label="RBI Handbook of Statistics on Indian States, Table 174 — State-wise Capital Outlay",
    )
    execution = _load(PROCESSED_DATA_DIR / "government-investment" / "capex-and-execution.json")
    private = _load(PROCESSED_DATA_DIR / "private-investment" / "investment-and-capacity.json")
    production = _load(PROCESSED_DATA_DIR / OUTPUTS["production"])
    return {
        "quality": build_investment_quality_payload(project_status, project_cost),
        "states": build_state_capex_evaluation_payload(current_gsdp, constant_gsdp, capital_outlay),
        "crowding_in": build_crowding_in_payload(execution, private, production),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for key, payload in build_depth_payloads().items():
        destination = PROCESSED_DATA_DIR / OUTPUTS[key]
        publish_json(payload, destination, "dated_multi_series.schema.json")
        LOGGER.info("Published %s", destination)


if __name__ == "__main__":
    main()
