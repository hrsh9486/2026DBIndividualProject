"""Final execution and fiscal-sustainability JSON builders."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from builders.dated_multi_series import (
    DatedSeriesDefinition,
    build_dated_multi_series_payload,
    metric_source_rows,
    select_metric_records,
    structural_definitions,
)
from config.capex_structural import get_capex_structural_bundle
from models import CanonicalRecord, ObservationStatus
from models.capex_metrics import FiscalMetrics, GovernmentMetrics
from validators import validate_dated_payload_quality


EXECUTION_KEYS = (
    "actual_capex_pct_gdp",
    "actual_capex_pct_total_expenditure",
    "capex_execution_ratio",
    "capex_budget_estimate",
    "capex_revised_estimate",
    "capex_actual",
)
FISCAL_KEYS = (
    "general_government_debt_pct_gdp",
    "interest_payments_pct_revenue",
    "interest_payments_pct_expenditure",
    "primary_balance_pct_gdp",
)


def _nominal_growth_records(government: GovernmentMetrics) -> tuple[CanonicalRecord, ...]:
    actual = [
        record for record in government.records
        if record.indicator == "capex_actual" and record.date >= date(2018, 3, 31)
    ]
    growth = []
    previous = None
    for record in actual:
        value = (
            None
            if previous in (None, 0) or record.value is None
            else (record.value / previous - 1) * 100
        )
        growth.append(replace(
            record,
            indicator="nominal_capex_growth",
            value=value,
            unit="percent",
            is_derived=True,
            method=(
                "Year-on-year percentage change in actual nominal "
                "central-government capital expenditure"
            ),
        ))
        if record.value is not None:
            previous = record.value
    return tuple(growth)


def build_execution_payload(government: GovernmentMetrics) -> dict:
    """Build capex-execution.json from GovernmentMetrics."""
    bundle = get_capex_structural_bundle("government_investment")
    records = select_metric_records(
        government.records,
        EXECUTION_KEYS,
        date(2018, 3, 31),
    )
    records += _nominal_growth_records(government)
    definitions = structural_definitions(bundle, EXECUTION_KEYS) + (
        DatedSeriesDefinition(
            key="nominal_capex_growth",
            label="Actual CapEx growth",
            entity="IND",
            unit="percent",
            is_derived=True,
            methodology=(
                "Year-on-year percentage change in actual nominal "
                "central-government capital expenditure."
            ),
            source_note=(
                "Nominal growth is affected by inflation and does not measure project quality."
            ),
        ),
    )
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="GOVERNMENT_INVESTMENT_CAPEX_EXECUTION",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=metric_source_rows(government.sources),
        methodology=(
            "Each fiscal year's original BE, later RE and eventual actual are retained "
            "from separate Union Budget vintages; execution is actual divided by original BE."
        ),
        note=(
            f"{bundle.limitation} Real CapEx growth is not published until a consistent "
            "government-investment deflator is registered; nominal growth is explicitly labelled."
        ),
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=EXECUTION_KEYS,
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


def _fiscal_bridge_records(
    government: GovernmentMetrics,
    fiscal: FiscalMetrics,
) -> tuple[CanonicalRecord, ...]:
    capex_share = {
        record.date: record
        for record in government.records
        if record.indicator == "actual_capex_pct_total_expenditure"
        and record.date >= date(2018, 3, 31)
    }
    interest_share = {
        record.date: record
        for record in fiscal.records
        if record.indicator == "interest_payments_pct_expenditure"
        and record.value is not None
    }
    records = []
    for record_date in sorted(capex_share):
        capex = capex_share[record_date]
        records.append(replace(
            capex,
            indicator="actual_capex_pct_expenditure",
            method="Actual central-government CapEx / actual total expenditure * 100",
        ))
        interest = interest_share.get(record_date)
        if capex.value is None or interest is None or interest.value in (None, 0):
            continue
        status = interest.status if interest.status != ObservationStatus.ACTUAL else capex.status
        records.append(replace(
            capex,
            indicator="capex_to_interest_allocation_ratio",
            value=capex.value / interest.value,
            unit="ratio",
            status=status,
            is_derived=True,
            method=(
                "Actual CapEx share of total expenditure divided by interest "
                "payments share of total expenditure"
            ),
        ))
    return tuple(records)


def build_fiscal_sustainability_payload(
    fiscal: FiscalMetrics,
    government: GovernmentMetrics,
    summary: dict,
) -> dict:
    """Build fiscal-sustainability.json from FiscalMetrics and GovernmentMetrics."""
    bundle = get_capex_structural_bundle("fiscal_capacity")
    records = select_metric_records(
        fiscal.records,
        FISCAL_KEYS,
        date(2011, 3, 31),
    )
    records += _fiscal_bridge_records(government, fiscal)
    definitions = structural_definitions(bundle, FISCAL_KEYS) + (
        DatedSeriesDefinition(
            key="actual_capex_pct_expenditure",
            label="Actual CapEx as share of expenditure",
            entity="IND",
            unit="percent",
            is_derived=True,
            methodology="actual_capex / actual_total_expenditure * 100",
            source_note="Accounting classification does not measure asset quality.",
        ),
        DatedSeriesDefinition(
            key="capex_to_interest_allocation_ratio",
            label="CapEx-to-interest allocation ratio",
            entity="IND",
            unit="ratio",
            is_derived=True,
            methodology=(
                "Actual CapEx share of total expenditure divided by interest payments "
                "share of total expenditure."
            ),
            source_note=(
                "This is an expenditure-allocation ratio, not a benefit-cost ratio "
                "or debt-sustainability threshold."
            ),
        ),
    )
    payload = build_dated_multi_series_payload(
        records,
        definitions,
        indicator_code="FISCAL_CAPACITY_DEBT_SUSTAINABILITY",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=metric_source_rows(fiscal.sources),
        methodology=(
            "Debt uses RBI adjusted combined Centre-and-State liabilities. Interest "
            "ratios divide consistent percentage-of-GDP components; primary balance "
            "is the negative of the reported gross primary deficit."
        ),
        note=bundle.limitation,
    )
    payload["metadata"]["transmission_evidence"] = [
        {
            "key": item["key"],
            "status": item["status"],
            "interpretation": item["interpretation"],
        }
        for item in summary["hypotheses"]
    ]
    validate_dated_payload_quality(
        payload,
        required_non_empty=FISCAL_KEYS,
        bounds={
            "general_government_debt_pct_gdp": (0, None),
            "interest_payments_pct_revenue": (0, None),
            "interest_payments_pct_expenditure": (0, 100),
        },
    )
    return payload
