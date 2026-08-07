"""Final sector-performance and correlation JSON builders."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.capex_analysis import CAPEX_MARKETS
from models.capex_metrics import GovernmentMetrics, PrivateMetrics
from transforms.capex_analysis import (
    build_lag_analysis,
    build_sector_performance_payload,
)


@dataclass(frozen=True, slots=True)
class CorrelationBuildResult:
    payload: dict
    estimates: dict


def build_sector_payload(prices: pd.DataFrame) -> dict:
    """Build sector-performance.json from the extracted price matrix."""
    definitions = {
        market.key: {
            "label": market.label,
            "ticker": market.ticker,
            "role": market.role,
        }
        for market in CAPEX_MARKETS
    }
    return build_sector_performance_payload(prices, definitions)


def build_correlations_payload(
    government: GovernmentMetrics,
    sector_payload: dict,
    private: PrivateMetrics,
) -> CorrelationBuildResult:
    """Build capex-sector-correlations.json and retain typed assembly metadata."""
    payload, estimates = build_lag_analysis(government, sector_payload, private)
    return CorrelationBuildResult(payload=payload, estimates=estimates)
