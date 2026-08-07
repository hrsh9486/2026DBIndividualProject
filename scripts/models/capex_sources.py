"""Typed containers passed from CapEx extraction to artifact construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class StructuralSources:
    budget_snapshots: tuple[Any, ...]
    nominal_gdp: Any
    national_accounts: Any
    obicus: Any
    debt: Any
    fiscal: Any


@dataclass(frozen=True, slots=True)
class AnalysisSources:
    prices: pd.DataFrame
    corporate_records: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class DepthSources:
    project_status: Any
    project_cost: Any
    current_gsdp: Any
    constant_gsdp: Any
    capital_outlay: Any


@dataclass(frozen=True, slots=True)
class SourceReference:
    name: str
    url: str
    retrieved_at: str


@dataclass(frozen=True, slots=True)
class AnnualSourceObservation:
    fiscal_period: str
    value: float
    status: str


@dataclass(frozen=True, slots=True)
class AnnualSourceSeries:
    key: str
    observations: tuple[AnnualSourceObservation, ...]


@dataclass(frozen=True, slots=True)
class AnnualSourceDataset:
    key: str
    references: tuple[SourceReference, ...]
    series: tuple[AnnualSourceSeries, ...]


@dataclass(frozen=True, slots=True)
class DeliverySources:
    allocation: AnnualSourceDataset
    delivery: AnnualSourceDataset
    production: AnnualSourceDataset
    reference_path: Path
    checksum: str


@dataclass(frozen=True, slots=True)
class CapexSources:
    structural: StructuralSources
    analysis: AnalysisSources
    depth: DepthSources
    delivery: DeliverySources


@dataclass(frozen=True, slots=True)
class CorporateFundamental:
    company_key: str
    company_label: str
    group: str
    fiscal_end: pd.Timestamp
    revenue: float | None
    ebitda: float | None
    capex: float | None
    net_ppe: float | None
    debt: float | None
    roce_proxy: float | None


@dataclass(frozen=True, slots=True)
class WorkbookSheet:
    name: str
    rows: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True, slots=True)
class RbiHandbookResponse:
    table_number: int
    table_label: str
    sheets: tuple[WorkbookSheet, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


@dataclass(frozen=True, slots=True)
class UnionBudgetSnapshot:
    edition_start_year: int
    actual_capex: float
    prior_budget_capex: float
    prior_revised_capex: float
    current_budget_capex: float
    actual_total_expenditure: float
    prior_budget_total_expenditure: float
    prior_revised_total_expenditure: float
    current_budget_total_expenditure: float
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


@dataclass(frozen=True, slots=True)
class NationalAccountsObservation:
    fiscal_start_year: int
    nominal_gdp_crore: float
    total_gfcf_crore: float
    private_corporate_gfcf_crore: float


@dataclass(frozen=True, slots=True)
class NationalAccountsResponse:
    observations: tuple[NationalAccountsObservation, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


@dataclass(frozen=True, slots=True)
class ObicusObservation:
    fiscal_start_year: int
    quarter: int
    responding_companies: int
    capacity_utilisation: float
    seasonally_adjusted_capacity_utilisation: float


@dataclass(frozen=True, slots=True)
class ObicusResponse:
    observations: tuple[ObicusObservation, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str
