"""Explicit source-to-artifact assembly for all thirteen final CapEx outputs."""

from __future__ import annotations

from dataclasses import dataclass

from builders.evaluation_outputs import (
    build_crowding_in_payload,
    build_quality_payload,
    build_states_payload,
    build_summary_payload,
)
from builders.fiscal_outputs import (
    build_execution_payload,
    build_fiscal_sustainability_payload,
)
from builders.market_outputs import (
    build_correlations_payload,
    build_sector_payload,
)
from builders.real_economy_outputs import (
    build_allocation_payload,
    build_corporate_payload,
    build_delivery_payload,
    build_private_response_payload,
    build_production_payload,
)
from models.capex_sources import CapexSources
from transforms.capex_metrics import (
    calculate_fiscal_metrics,
    calculate_government_metrics,
    calculate_private_metrics,
)


@dataclass(frozen=True, slots=True)
class CapexArtifacts:
    outputs: dict[str, dict]


def build_capex_artifacts(sources: CapexSources) -> CapexArtifacts:
    """Calculate typed metrics, then call every final output builder explicitly."""
    government = calculate_government_metrics(
        sources.structural.budget_snapshots,
        sources.structural.nominal_gdp,
    )
    private = calculate_private_metrics(
        sources.structural.national_accounts,
        government,
        sources.structural.obicus,
    )
    fiscal = calculate_fiscal_metrics(
        sources.structural.debt,
        sources.structural.fiscal,
    )

    execution = build_execution_payload(government)
    allocation = build_allocation_payload(sources.delivery.allocation)
    delivery = build_delivery_payload(sources.delivery.delivery)
    production = build_production_payload(sources.delivery.production)
    sectors = build_sector_payload(sources.analysis.prices)
    correlation_result = build_correlations_payload(government, sectors, private)
    private_response = build_private_response_payload(private)
    summary = build_summary_payload(
        government,
        private,
        fiscal,
        correlation_result.estimates,
    )
    fiscal_sustainability = build_fiscal_sustainability_payload(
        fiscal,
        government,
        summary,
    )
    corporate = build_corporate_payload(sources.analysis.corporate_records)
    quality = build_quality_payload(sources.depth)
    states = build_states_payload(sources.depth)
    crowding_in = build_crowding_in_payload(
        government,
        private,
        sources.delivery.production,
    )

    return CapexArtifacts(outputs={
        "execution": execution,
        "allocation": allocation,
        "delivery": delivery,
        "production": production,
        "sectors": sectors,
        "correlations": correlation_result.payload,
        "private": private_response,
        "fiscal": fiscal_sustainability,
        "summary": summary,
        "corporate": corporate,
        "quality": quality,
        "states": states,
        "crowding_in": crowding_in,
    })
