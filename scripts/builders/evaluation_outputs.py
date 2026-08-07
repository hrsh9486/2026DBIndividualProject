"""Final quality, state, crowding-in and summary JSON builders."""

from __future__ import annotations

from models.capex_metrics import FiscalMetrics, GovernmentMetrics, PrivateMetrics
from models.capex_sources import AnnualSourceDataset, DepthSources
from transforms.capex_analysis import classify_summary
from transforms.capex_depth import (
    build_crowding_in_payload as transform_crowding_in_payload,
    build_investment_quality_payload,
    build_state_capex_evaluation_payload,
)


def build_quality_payload(sources: DepthSources) -> dict:
    """Build investment-quality.json from typed project source responses."""
    return build_investment_quality_payload(
        sources.project_status,
        sources.project_cost,
    )


def build_states_payload(sources: DepthSources) -> dict:
    """Build state-capex-evaluation.json from typed state source responses."""
    return build_state_capex_evaluation_payload(
        sources.current_gsdp,
        sources.constant_gsdp,
        sources.capital_outlay,
    )


def build_crowding_in_payload(
    government: GovernmentMetrics,
    private: PrivateMetrics,
    production: AnnualSourceDataset,
) -> dict:
    """Build crowding-in-evidence.json from typed metrics and IIP observations."""
    return transform_crowding_in_payload(government, private, production)


def build_summary_payload(
    government: GovernmentMetrics,
    private: PrivateMetrics,
    fiscal: FiscalMetrics,
    correlation_estimates: dict,
) -> dict:
    """Build analysis-summary.json from typed metrics and correlation estimates."""
    return classify_summary(
        government,
        private,
        fiscal,
        correlation_estimates,
    )
