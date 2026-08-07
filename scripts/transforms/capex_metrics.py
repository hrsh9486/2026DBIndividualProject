"""Create typed structural metrics without constructing JSON payloads."""

from __future__ import annotations

from models.capex_metrics import (
    FiscalMetrics,
    GovernmentMetrics,
    MetricSource,
    PrivateMetrics,
)
from models.capex_sources import (
    NationalAccountsResponse,
    ObicusResponse,
    RbiHandbookResponse,
    UnionBudgetSnapshot,
)
from transforms.fiscal_capacity import build_fiscal_capacity_records
from transforms.government_investment import (
    build_government_investment_records,
    parse_nominal_gdp_by_fiscal_year,
)
from transforms.private_investment import (
    build_capacity_utilisation_records,
    build_lagged_public_capex_records,
    build_private_investment_records,
)
from validators import validate_records


def calculate_government_metrics(
    snapshots: tuple[UnionBudgetSnapshot, ...],
    gdp_response: RbiHandbookResponse,
) -> GovernmentMetrics:
    """Calculate government metrics and retain their source provenance."""
    nominal_gdp = parse_nominal_gdp_by_fiscal_year(gdp_response)
    records = tuple(build_government_investment_records(
        snapshots,
        nominal_gdp_by_fiscal_year=nominal_gdp,
    ))
    validate_records(records, expected_frequency="annual")
    sources = tuple(
        MetricSource(
            name=(
                f"Union Budget {snapshot.edition_start_year}-"
                f"{str(snapshot.edition_start_year + 1)[-2:]}"
            ),
            url=snapshot.source_url,
            retrieved_at=snapshot.retrieved_at,
        )
        for snapshot in snapshots
    ) + (
        MetricSource(
            name=gdp_response.table_label,
            url=gdp_response.source_url,
            retrieved_at=gdp_response.retrieved_at,
        ),
    )
    return GovernmentMetrics(records=records, sources=sources)


def calculate_private_metrics(
    response: NationalAccountsResponse,
    government: GovernmentMetrics,
    obicus_response: ObicusResponse,
) -> PrivateMetrics:
    """Calculate private-investment metrics using typed government records."""
    records = build_private_investment_records(response)
    records.extend(build_lagged_public_capex_records(government.records))
    records.extend(build_capacity_utilisation_records(obicus_response))
    validated = tuple(validate_records(records))
    return PrivateMetrics(
        records=validated,
        sources=(
            MetricSource(
                name="MoSPI new-series GDP estimates — Statement 7.1B",
                url=response.source_url,
                retrieved_at=response.retrieved_at,
            ),
            MetricSource(name="Calculated GovernmentMetrics"),
            MetricSource(
                name="RBI OBICUS — Table 1 Capacity Utilisation",
                url=obicus_response.source_url,
                retrieved_at=obicus_response.retrieved_at,
            ),
        ),
    )


def calculate_fiscal_metrics(
    debt_response: RbiHandbookResponse,
    fiscal_response: RbiHandbookResponse,
) -> FiscalMetrics:
    """Calculate fiscal metrics and retain their source provenance."""
    records = tuple(build_fiscal_capacity_records(debt_response, fiscal_response))
    validate_records(records, expected_frequency="annual")
    return FiscalMetrics(
        records=records,
        sources=tuple(
            MetricSource(
                name=response.table_label,
                url=response.source_url,
                retrieved_at=response.retrieved_at,
            )
            for response in (debt_response, fiscal_response)
        ),
    )
