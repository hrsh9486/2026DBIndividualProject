"""Definitions for the three structural inputs used by the CapEx product."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CapexUpstreamSeries:
    key: str
    label: str
    unit: str
    frequency: str
    source: str
    source_field: str
    definition: str
    transformation: str | None
    limitation: str
    is_derived: bool = False


@dataclass(frozen=True, slots=True)
class CapexUpstreamBundle:
    key: str
    label: str
    research_question: str
    output_path: str
    frequency: str
    primary_series: tuple[str, ...]
    supporting_series: tuple[str, ...]
    limitation: str
    series: tuple[CapexUpstreamSeries, ...]


def _series(key, label, unit, frequency, source, source_field, definition, transformation, limitation, *, derived=False):
    return CapexUpstreamSeries(
        key, label, unit, frequency, source, source_field, definition,
        transformation, limitation, derived,
    )


CAPEX_UPSTREAM_BUNDLES: dict[str, CapexUpstreamBundle] = {
    bundle.key: bundle
    for bundle in (
        CapexUpstreamBundle(
            key="government_investment",
            label="Government investment and execution",
            research_question="Is central-government spending shifting toward productive assets, and are budget plans delivered?",
            output_path="government-investment/capex-and-execution.json",
            frequency="annual",
            primary_series=("actual_capex_pct_gdp", "actual_capex_pct_total_expenditure"),
            supporting_series=("capex_execution_ratio", "capex_budget_estimate", "capex_revised_estimate", "capex_actual"),
            limitation="Fiscal expenditure measures effort and execution, not whether projects were completed well or were productive.",
            series=(
                _series("actual_capex_pct_gdp", "Actual central-government capital expenditure", "percent", "fiscal_year", "Union Budget + MoSPI", "Capital expenditure actual; nominal GDP", "Direct central-government capital expenditure as a share of nominal GDP.", "actual_capex / nominal_gdp * 100", "Excludes broader effective CapEx unless separately labelled.", derived=True),
                _series("actual_capex_pct_total_expenditure", "Actual CapEx share of expenditure", "percent", "fiscal_year", "Union Budget", "Actual capital and total expenditure", "Actual capital expenditure as a share of actual total expenditure.", "actual_capex / actual_total_expenditure * 100", "Accounting classification does not measure asset quality.", derived=True),
                _series("capex_execution_ratio", "CapEx execution ratio", "percent", "fiscal_year", "Union Budget", "Actual and original Budget Estimate", "Actual capital expenditure relative to the original Budget Estimate.", "actual_capex / budget_estimate_capex * 100", "A ratio above 100 may reflect supplemental spending rather than superior execution.", derived=True),
                _series("capex_budget_estimate", "Capital expenditure — Budget Estimate", "INR_crore", "fiscal_year", "Union Budget", "Budget Estimate capital expenditure", "Original central-government capital expenditure plan.", None, "Budget estimates are plans, not delivered spending."),
                _series("capex_revised_estimate", "Capital expenditure — Revised Estimate", "INR_crore", "fiscal_year", "Union Budget", "Revised Estimate capital expenditure", "In-year revised central-government capital expenditure plan.", None, "Revised estimates remain estimates."),
                _series("capex_actual", "Capital expenditure — Actual", "INR_crore", "fiscal_year", "Union Budget", "Actual capital expenditure", "Out-turn central-government capital expenditure.", None, "Latest actuals lag budget estimates."),
            ),
        ),
        CapexUpstreamBundle(
            key="private_investment",
            label="Private investment and crowding-in",
            research_question="Is public infrastructure investment associated with firms expanding productive capacity?",
            output_path="private-investment/investment-and-capacity.json",
            frequency="mixed",
            primary_series=("private_corporate_gfcf_pct_gdp", "manufacturing_capacity_utilisation"),
            supporting_series=("private_share_total_gfcf", "public_capex_lagged"),
            limitation="Co-movement cannot establish crowding-in; demand, profitability, rates and global conditions also drive investment.",
            series=(
                _series("private_corporate_gfcf_pct_gdp", "Private corporate GFCF", "percent", "annual", "MoSPI National Accounts", "Institutional-sector private corporate GFCF; nominal GDP", "Private corporate fixed investment relative to nominal GDP.", "private_corporate_gfcf / nominal_gdp * 100", "Institutional-sector revisions and base-year changes create breaks.", derived=True),
                _series("private_share_total_gfcf", "Private corporate share of GFCF", "percent", "annual", "MoSPI National Accounts", "Private corporate and total GFCF", "Private corporate share of total fixed-capital formation.", "private_corporate_gfcf / total_gfcf * 100", "This is not the whole private sector if household investment is excluded.", derived=True),
                _series("manufacturing_capacity_utilisation", "Manufacturing capacity utilisation", "percent", "quarterly", "RBI OBICUS", "Aggregate reported capacity utilisation", "Unadjusted aggregate manufacturing capacity utilisation.", None, "OBICUS is a voluntary survey and does not cover the entire manufacturing universe."),
                _series("public_capex_lagged", "Public CapEx, lagged one year", "percent", "annual", "Union Budget + MoSPI", "Actual CapEx/GDP", "Actual central-government CapEx/GDP shifted forward one year for visual comparison.", "lag(actual_capex_pct_gdp, 1 year)", "A chosen lag is descriptive and not a causal estimate.", derived=True),
            ),
        ),
        CapexUpstreamBundle(
            key="fiscal_capacity",
            label="Fiscal capacity and debt sustainability",
            research_question="Can general-government investment be sustained without debt service crowding out future spending?",
            output_path="fiscal-capacity/debt-and-interest-burden.json",
            frequency="annual",
            primary_series=("general_government_debt_pct_gdp", "interest_payments_pct_revenue"),
            supporting_series=("interest_payments_pct_expenditure", "primary_balance_pct_gdp", "central_government_debt_pct_gdp"),
            limitation="Debt sustainability depends on growth, interest rates, maturity, currency and expenditure quality, not one threshold.",
            series=(
                _series("general_government_debt_pct_gdp", "General-government debt", "percent", "fiscal_year", "RBI / Economic Survey", "Combined central and state liabilities; nominal GDP", "General-government debt stock relative to GDP.", None, "Coverage must remain consistent across vintages."),
                _series("interest_payments_pct_revenue", "Interest payments as share of revenue", "percent", "fiscal_year", "Union Budget", "Actual interest payments; actual revenue receipts", "Central-government interest payments relative to revenue receipts.", "interest_payments / revenue_receipts * 100", "Central-government burden is narrower than general-government debt.", derived=True),
                _series("interest_payments_pct_expenditure", "Interest payments as share of expenditure", "percent", "fiscal_year", "Union Budget", "Actual interest payments; actual total expenditure", "Interest payments relative to total expenditure.", "interest_payments / total_expenditure * 100", "Changes in total expenditure alter the ratio independently of interest costs.", derived=True),
                _series("primary_balance_pct_gdp", "Primary balance", "percent", "fiscal_year", "RBI / Union Budget", "Fiscal balance excluding net interest; nominal GDP", "Primary balance using negative values for deficits.", "-(fiscal_deficit - interest_payments) / nominal_gdp * 100", "Sign convention must be retained in presentation.", derived=True),
                _series("central_government_debt_pct_gdp", "Central-government debt", "percent", "annual", "RBI", "Central-government debt; GDP", "Central-government debt as a secondary decomposition series.", None, "Not comparable to general-government debt."),
            ),
        ),
    )
}


def get_capex_upstream_bundle(key: str) -> CapexUpstreamBundle:
    try:
        return CAPEX_UPSTREAM_BUNDLES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown CapEx structural bundle {key!r}") from exc
