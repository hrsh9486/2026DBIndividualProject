"""Fiscal-vintage-safe government-investment calculations."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence

from models.capex_sources import RbiHandbookResponse, UnionBudgetSnapshot
from models import CanonicalRecord, FiscalPeriod, ObservationStatus


def build_government_investment_records(
    snapshots: Sequence[UnionBudgetSnapshot],
    *,
    nominal_gdp_by_fiscal_year: Mapping[int, tuple[float, ObservationStatus]] | None = None,
) -> list[CanonicalRecord]:
    """Reconstruct BE, RE and actual CapEx without overwriting vintages."""
    budget: dict[int, tuple[float, UnionBudgetSnapshot]] = {}
    revised: dict[int, tuple[float, UnionBudgetSnapshot]] = {}
    actual: dict[int, tuple[float, float, UnionBudgetSnapshot]] = {}
    ordered_snapshots = sorted(
        (snapshot.edition_start_year, index, snapshot)
        for index, snapshot in enumerate(snapshots)
    )
    for _edition_start_year, _index, snapshot in ordered_snapshots:
        budget[snapshot.edition_start_year] = (snapshot.current_budget_capex, snapshot)
        revised[snapshot.edition_start_year - 1] = (snapshot.prior_revised_capex, snapshot)
        actual[snapshot.edition_start_year - 2] = (
            snapshot.actual_capex,
            snapshot.actual_total_expenditure,
            snapshot,
        )

    records: list[CanonicalRecord] = []
    nominal_gdp_by_fiscal_year = nominal_gdp_by_fiscal_year or {}
    for fiscal_year in sorted(set(budget) | set(revised) | set(actual)):
        period = FiscalPeriod(fiscal_year)
        common = {
            "date": period.end_date,
            "entity": "IND",
            "frequency": "annual",
            "source": "Union Budget — Budget at a Glance",
            "period_label": period.label,
            "period_start": period.start_date,
            "period_end": period.end_date,
        }
        if fiscal_year in budget:
            value, snapshot = budget[fiscal_year]
            records.append(CanonicalRecord(
                indicator="capex_budget_estimate",
                value=value,
                unit="INR_crore",
                status=ObservationStatus.BUDGET,
                vintage=f"Budget {snapshot.edition_start_year}-{str(snapshot.edition_start_year + 1)[-2:]}",
                source_url=snapshot.source_url,
                retrieved_at=datetime.fromisoformat(snapshot.retrieved_at),
                **common,
            ))
        if fiscal_year in revised:
            value, snapshot = revised[fiscal_year]
            records.append(CanonicalRecord(
                indicator="capex_revised_estimate",
                value=value,
                unit="INR_crore",
                status=ObservationStatus.ESTIMATE,
                vintage=f"Budget {snapshot.edition_start_year}-{str(snapshot.edition_start_year + 1)[-2:]}",
                source_url=snapshot.source_url,
                retrieved_at=datetime.fromisoformat(snapshot.retrieved_at),
                **common,
            ))
        if fiscal_year in actual:
            capex, total_expenditure, snapshot = actual[fiscal_year]
            provenance = {
                "source_url": snapshot.source_url,
                "retrieved_at": datetime.fromisoformat(snapshot.retrieved_at),
                "vintage": f"Budget {snapshot.edition_start_year}-{str(snapshot.edition_start_year + 1)[-2:]}",
            }
            records.extend((
                CanonicalRecord(
                    indicator="capex_actual",
                    value=capex,
                    unit="INR_crore",
                    status=ObservationStatus.ACTUAL,
                    **provenance,
                    **common,
                ),
                CanonicalRecord(
                    indicator="actual_capex_pct_total_expenditure",
                    value=capex / total_expenditure * 100 if total_expenditure else None,
                    unit="percent",
                    status=ObservationStatus.ACTUAL,
                    is_derived=True,
                    method="Actual capital expenditure / actual total expenditure * 100",
                    **provenance,
                    **common,
                ),
            ))
            nominal_gdp = nominal_gdp_by_fiscal_year.get(fiscal_year)
            if nominal_gdp and nominal_gdp[0] > 0:
                records.append(CanonicalRecord(
                    indicator="actual_capex_pct_gdp",
                    value=capex / nominal_gdp[0] * 100,
                    unit="percent",
                    status=nominal_gdp[1],
                    is_derived=True,
                    method="Actual central-government capital expenditure / fiscal-year nominal GDP * 100",
                    **provenance,
                    **common,
                ))
        if fiscal_year in actual and fiscal_year in budget:
            capex, _, actual_snapshot = actual[fiscal_year]
            budget_value, budget_snapshot = budget[fiscal_year]
            records.append(CanonicalRecord(
                indicator="capex_execution_ratio",
                value=capex / budget_value * 100 if budget_value else None,
                unit="percent",
                status=ObservationStatus.ACTUAL,
                is_derived=True,
                method="Actual capital expenditure / original Budget Estimate * 100",
                source_url=actual_snapshot.source_url,
                retrieved_at=datetime.fromisoformat(actual_snapshot.retrieved_at),
                vintage=f"BE {budget_snapshot.edition_start_year}; actual {actual_snapshot.edition_start_year}",
                **common,
            ))
    return records


def parse_nominal_gdp_by_fiscal_year(
    response: RbiHandbookResponse,
) -> dict[int, tuple[float, ObservationStatus]]:
    """Parse current-price fiscal-year GDP from the RBI/NSO macro table."""
    output: dict[int, tuple[float, ObservationStatus]] = {}
    for sheet in response.sheets:
        header = next((row for row in sheet.rows if row and row[0] == "Item/Year"), None)
        gdp = next((row for row in sheet.rows if row and row[0] == "Gross Domestic Product"), None)
        if header is None or gdp is None:
            continue
        for fiscal_label, value in zip(header[1:], gdp[1:]):
            if not isinstance(fiscal_label, str) or not isinstance(value, (int, float)):
                continue
            start_year = int(fiscal_label[:4])
            status = ObservationStatus.ACTUAL
            if start_year == 2023:
                status = ObservationStatus.REVISED
            elif start_year >= 2024:
                status = ObservationStatus.PROVISIONAL
            output[start_year] = (float(value), status)
    return output
