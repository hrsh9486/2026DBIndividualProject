"""Scope-locked definitions for the seven focused analytical bundles.

These definitions describe economic meaning and output expectations. Provider
request details remain in extractors and formulas remain in transforms.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.indicators import Contract


@dataclass(frozen=True, slots=True)
class FocusedSeriesSpec:
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
class FocusedBundleSpec:
    key: str
    label: str
    research_question: str
    output_path: str
    contract: Contract
    frequency: str
    primary_series: tuple[str, ...]
    supporting_series: tuple[str, ...]
    limitation: str
    series: tuple[FocusedSeriesSpec, ...]


def _series(key, label, unit, frequency, source, source_field, definition, transformation, limitation, *, derived=False):
    return FocusedSeriesSpec(
        key, label, unit, frequency, source, source_field, definition,
        transformation, limitation, derived,
    )


FOCUSED_BUNDLES: dict[str, FocusedBundleSpec] = {
    bundle.key: bundle
    for bundle in (
        FocusedBundleSpec(
            key="digital_integration",
            label="Digital integration and tax capacity",
            research_question="Is digital-payment adoption occurring alongside deeper participation and stronger tax capacity?",
            output_path="digital-integration/upi-and-tax-capacity.json",
            contract=Contract.DATED_MULTI_SERIES,
            frequency="mixed",
            primary_series=("upi_transactions_per_capita", "upi_value_pct_gdp"),
            supporting_series=("average_upi_transaction_value", "gst_growth_gap"),
            limitation="UPI use and GST receipts are associated measures, not proof that digital payments cause formalisation.",
            series=(
                _series("upi_transactions_per_capita", "UPI transactions per capita", "transactions_per_person", "monthly", "NPCI + World Bank", "UPI monthly volume; SP.POP.TOTL", "Monthly UPI transaction count divided by calendar-year population.", "volume_millions * 1,000,000 / annual_population; annual population is used for each month without interpolation", "Annual population denominators make within-year changes entirely transaction-driven.", derived=True),
                _series("upi_value_pct_gdp", "UPI value as share of GDP", "percent", "monthly", "NPCI + World Bank", "UPI monthly value; NY.GDP.MKTP.CN", "Trailing twelve-month UPI value relative to nominal GDP in current INR.", "rolling_12m_upi_value_inr / calendar_year_nominal_gdp_inr * 100", "UPI value includes transfers and is not value added; early months lack a 12-month window.", derived=True),
                _series("average_upi_transaction_value", "Average UPI transaction value", "INR", "monthly", "NPCI", "Monthly value (₹ crore) and volume (million)", "Average value of reported UPI transactions.", "value_crore * 10,000,000 / (volume_millions * 1,000,000)", "Mix shifts between person-to-person and merchant payments affect the average.", derived=True),
                _series("gst_growth_gap", "GST revenue growth minus nominal GDP growth", "percentage_points", "annual", "GST portal + MoSPI", "Gross GST receipts; nominal GDP", "Annual gross GST growth less nominal GDP growth.", "gst_yoy_pct - nominal_gdp_yoy_pct", "Tax-rate, enforcement, refund and import changes also affect GST receipts.", derived=True),
            ),
        ),
        FocusedBundleSpec(
            key="government_investment",
            label="Government investment and execution",
            research_question="Is central-government spending shifting toward productive assets, and are budget plans delivered?",
            output_path="government-investment/capex-and-execution.json",
            contract=Contract.DATED_MULTI_SERIES,
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
        FocusedBundleSpec(
            key="private_investment",
            label="Private investment and crowding-in",
            research_question="Is public infrastructure investment associated with firms expanding productive capacity?",
            output_path="private-investment/investment-and-capacity.json",
            contract=Contract.DATED_MULTI_SERIES,
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
        FocusedBundleSpec(
            key="fiscal_capacity",
            label="Fiscal capacity and debt sustainability",
            research_question="Can general-government investment be sustained without debt service crowding out future spending?",
            output_path="fiscal-capacity/debt-and-interest-burden.json",
            contract=Contract.DATED_MULTI_SERIES,
            frequency="annual",
            primary_series=("general_government_debt_pct_gdp", "interest_payments_pct_revenue"),
            supporting_series=("interest_payments_pct_expenditure", "primary_balance_pct_gdp", "central_government_debt_pct_gdp"),
            limitation="Debt sustainability depends on growth, interest rates, maturity, currency and expenditure quality, not one threshold.",
            series=(
                _series("general_government_debt_pct_gdp", "General-government debt", "percent", "fiscal_year", "RBI / Economic Survey", "Combined central and state liabilities; nominal GDP", "General-government debt stock relative to GDP.", None, "Coverage must remain consistent across vintages."),
                _series("interest_payments_pct_revenue", "Interest payments as share of revenue", "percent", "fiscal_year", "Union Budget", "Actual interest payments; actual revenue receipts", "Central-government interest payments relative to revenue receipts.", "interest_payments / revenue_receipts * 100", "Central-government burden is narrower than general-government debt.", derived=True),
                _series("interest_payments_pct_expenditure", "Interest payments as share of expenditure", "percent", "fiscal_year", "Union Budget", "Actual interest payments; actual total expenditure", "Interest payments relative to total expenditure.", "interest_payments / total_expenditure * 100", "Changes in total expenditure alter the ratio independently of interest costs.", derived=True),
                _series("primary_balance_pct_gdp", "Primary balance", "percent", "fiscal_year", "RBI / Union Budget", "Fiscal balance excluding net interest; nominal GDP", "Primary balance using negative values for deficits.", "-(fiscal_deficit - interest_payments) / nominal_gdp * 100", "Sign convention must be retained in presentation.", derived=True),
                _series("central_government_debt_pct_gdp", "Central-government debt", "percent", "annual", "World Bank / RBI", "Central-government debt; GDP", "Central-government debt as a secondary decomposition series.", None, "Not comparable to general-government debt."),
            ),
        ),
        FocusedBundleSpec(
            key="external_competitiveness",
            label="External competitiveness and resilience",
            research_question="Is domestic growth occurring without persistent deterioration in external competitiveness?",
            output_path="external-competitiveness/reer-and-current-account.json",
            contract=Contract.DATED_MULTI_SERIES,
            frequency="mixed",
            primary_series=("reer_index", "reer_deviation_pct"),
            supporting_series=("current_account_pct_gdp", "non_oil_export_growth"),
            limitation="REER is a relative-price index, not an intrinsic fair-value estimate.",
            series=(
                _series("reer_index", "Trade-weighted REER", "index", "monthly", "RBI DBIE", "40-currency trade-weighted REER, 2015-16=100", "RBI trade-weighted real effective exchange-rate index.", None, "RBI may revise weights and base periods."),
                _series("reer_deviation_pct", "REER deviation from five-year average", "percent", "monthly", "RBI DBIE", "REER index", "Percentage deviation from the trailing 60-month mean.", "(reer / rolling_mean_60m - 1) * 100", "The historical mean is a reference, not fair value.", derived=True),
                _series("current_account_pct_gdp", "Current-account balance", "percent", "quarterly", "RBI DBIE + MoSPI", "Current-account balance; nominal GDP", "Current-account balance as a share of GDP; deficits are negative.", "current_account_balance / nominal_gdp * 100", "Quarterly GDP and balance-of-payments revisions must use matching vintages.", derived=True),
                _series("non_oil_export_growth", "Non-oil merchandise export growth", "percent", "monthly", "Department of Commerce", "Non-petroleum merchandise exports", "Year-on-year growth in non-oil merchandise exports.", "pct_change(value, 12) * 100", "Classification and price effects influence nominal export growth.", derived=True),
            ),
        ),
        FocusedBundleSpec(
            key="human_capital",
            label="Human-capital and employment conversion",
            research_question="Is higher-education expansion translating into productive employment?",
            output_path="human-capital/education-and-employment.json",
            contract=Contract.DATED_MULTI_SERIES,
            frequency="annual",
            primary_series=("tertiary_ger", "educated_unemployment"),
            supporting_series=("regular_salaried_employment_share",),
            limitation="Enrolment does not measure learning quality, and employment status does not establish skill use or job quality.",
            series=(
                _series("tertiary_ger", "Tertiary Gross Enrolment Ratio", "percent", "academic_year", "AISHE", "All-India GER, age 18-23", "Participation in tertiary education among the official age cohort.", None, "AISHE revisions and institution coverage must be preserved."),
                _series("educated_unemployment", "Secondary-and-above unemployment rate", "percent", "annual", "MoSPI PLFS", "Usual status (ps+ss), age 15+, secondary and above", "Published unemployment rate among people aged 15+ with secondary-or-higher education using usual status.", None, "The published aggregate is broader than graduate unemployment; it excludes people outside the labour force and can rise with participation."),
                _series("regular_salaried_employment_share", "Regular wage or salaried employment share", "percent", "annual", "MoSPI PLFS", "Usual-status workers by employment status, age 15+", "Share of employed people aged 15+ in regular wage or salaried work.", None, "Regular salaried work is not synonymous with formal or high-quality employment."),
            ),
        ),
        FocusedBundleSpec(
            key="capital_resilience",
            label="Domestic capital buffer against global shocks",
            research_question="Has domestic institutional investment reduced market sensitivity to foreign portfolio outflows?",
            output_path="capital-resilience/institutional-flows.json",
            contract=Contract.DATED_MULTI_SERIES,
            frequency="monthly",
            primary_series=("dii_net_flow", "fpi_net_flow"),
            supporting_series=("dii_rolling_12m", "fpi_rolling_12m", "dii_offset_ratio"),
            limitation="Institutional buying may reduce disruption without improving fundamentals and does not equal retail participation.",
            series=(
                _series("dii_net_flow", "DII net equity flow", "INR_crore", "monthly", "NSE", "Cash-market DII purchases minus sales", "Monthly sum of official daily net DII equity activity.", "sum daily net values by calendar month", "Exchange activity definitions and coverage must remain stable.", derived=True),
                _series("fpi_net_flow", "FII/FPI net equity flow", "INR_crore", "monthly", "NSE", "Cash-market FII/FPI purchases minus sales", "Monthly sum of official daily net FII/FPI equity activity.", "sum daily net values by calendar month", "NSE activity is not identical to NSDL custodial flow data.", derived=True),
                _series("dii_rolling_12m", "DII rolling 12-month flow", "INR_crore", "monthly", "NSE", "Monthly DII net flow", "Trailing 12-month cumulative DII flow.", "rolling_sum(dii_net_flow, 12)", "Early observations lack a full window.", derived=True),
                _series("fpi_rolling_12m", "FPI rolling 12-month flow", "INR_crore", "monthly", "NSE", "Monthly FPI net flow", "Trailing 12-month cumulative FPI flow.", "rolling_sum(fpi_net_flow, 12)", "Early observations lack a full window.", derived=True),
                _series("dii_offset_ratio", "DII offset ratio", "ratio", "monthly", "NSE", "Monthly DII and FPI net flows", "Domestic buying divided by the magnitude of foreign selling in FPI selling months; null otherwise.", "max(dii_net_flow, 0) / abs(fpi_net_flow) when fpi_net_flow < 0", "Ratios above one do not imply that DII caused market stability.", derived=True),
            ),
        ),
    )
}


def get_focused_bundle(key: str) -> FocusedBundleSpec:
    try:
        return FOCUSED_BUNDLES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown focused bundle {key!r}") from exc
