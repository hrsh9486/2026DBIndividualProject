"""Reusable deterministic calculations, independent of source I/O."""

from .digital_integration import build_gst_growth_gap_records, build_upi_canonical_records
from .government_investment import build_government_investment_records, parse_nominal_gdp_by_fiscal_year
from .external_competitiveness import build_external_competitiveness_records
from .fiscal_capacity import build_fiscal_capacity_records
from .private_investment import build_capacity_utilisation_records, build_private_investment_records
from .human_capital import build_human_capital_records
from .capital_resilience import build_capital_resilience_records

__all__ = [
    "build_government_investment_records",
    "parse_nominal_gdp_by_fiscal_year",
    "build_external_competitiveness_records",
    "build_fiscal_capacity_records",
    "build_private_investment_records",
    "build_human_capital_records",
    "build_capital_resilience_records",
    "build_market_bundle",
    "build_upi_canonical_records",
    "build_gst_growth_gap_records",
    "build_capacity_utilisation_records",
]


def __getattr__(name: str):
    """Load the optional pandas/numpy market stack only when it is requested."""
    if name == "build_market_bundle":
        from .market_stats import build_market_bundle

        return build_market_bundle
    raise AttributeError(name)
