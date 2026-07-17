"""Indicator registry: the single source of truth for pipeline definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Source(str, Enum):
    WORLD_BANK = "world_bank"
    YFINANCE = "yfinance"


class Contract(str, Enum):
    ANNUAL_COUNTRY_SERIES = "annual_country_series.schema.json"
    DATED_MULTI_SERIES = "dated_multi_series.schema.json"
    MARKET_PERFORMANCE = "market_performance.schema.json"


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    key: str
    label: str
    source: Source
    source_id: str
    frequency: str
    unit: str
    contract: Contract
    output_path: str
    category: str
    is_derived: bool = False
    methodology: str | None = None
    note: str | None = None


def _world_bank(
    key: str,
    label: str,
    source_id: str,
    category: str,
    output_file: str,
    *,
    unit: str = "percent",
    is_derived: bool = False,
    methodology: str | None = None,
) -> IndicatorSpec:
    return IndicatorSpec(
        key=key,
        label=label,
        source=Source.WORLD_BANK,
        source_id=source_id,
        frequency="annual",
        unit=unit,
        contract=Contract.ANNUAL_COUNTRY_SERIES,
        output_path=f"{category}/{output_file}",
        category=category,
        is_derived=is_derived,
        methodology=methodology,
    )


INDICATORS: dict[str, IndicatorSpec] = {
    spec.key: spec
    for spec in (
        _world_bank("urban_population_pct", "Urban population (% of total)", "SP.URB.TOTL.IN.ZS", "employment", "urban_population.json"),
        _world_bank("adult_literacy_rate", "Adult literacy rate (% ages 15+)", "SE.ADT.LITR.ZS", "education", "literacy_rate.json"),
        _world_bank("labour_force_participation", "Labour force participation rate (% ages 15+)", "SL.TLF.CACT.ZS", "employment", "labor_force_participation.json"),
        _world_bank("working_age_share_pct", "Working-age population share (% ages 15-64)", "SP.POP.1564.TO.ZS", "employment", "working_age_share_pct.json"),
        _world_bank("youth_unemployment_rate", "Youth unemployment rate (% ages 15-24)", "SL.UEM.1524.ZS", "employment", "youth_unemployment_rate.json"),
        _world_bank("female_to_male_lfpr_ratio", "Female-to-male LFPR ratio", "SL.TLF.CACT.FM.NE.ZS", "employment", "female_to_male_lfpr_ratio.json", unit="percent"),
        _world_bank("secondary_enrolment", "Secondary gross enrolment ratio", "SE.SEC.ENRR", "education", "school_enrollment_gross_secondary.json"),
        _world_bank("tertiary_enrolment", "Tertiary gross enrolment ratio", "SE.TER.ENRR", "education", "school_enrollment_gross_tertiary.json"),
        _world_bank("secondary_education_expenditure", "Government expenditure per secondary student", "SE.XPD.SECO.PC.ZS", "education", "pct_gdp_secondary_expenditure.json"),
        _world_bank("real_effective_exchange_rate", "Real effective exchange rate", "PX.REX.REER", "currency", "real_effective_exchange_rate.json", unit="index"),
        _world_bank("central_government_debt_pct_gdp", "Central government debt (% of GDP)", "GC.DOD.TOTL.GD.ZS", "macro", "central_government_debt.json"),
        _world_bank("fdi_net_inflows_pct_gdp", "FDI net inflows (% of GDP)", "BX.KLT.DINV.WD.GD.ZS", "trade", "fdi_net_inflows.json"),
        _world_bank("medium_high_tech_exports", "Medium- and high-technology exports (% manufactured exports)", "TX.MNF.TECH.ZS.UN", "trade", "medium_high_tech_exports.json"),
    )
}


def get_indicator(key: str) -> IndicatorSpec:
    """Return an indicator definition or raise a useful error."""
    try:
        return INDICATORS[key]
    except KeyError as exc:
        known = ", ".join(sorted(INDICATORS))
        raise KeyError(f"Unknown indicator {key!r}. Known indicators: {known}") from exc


def indicators_for(source: Source) -> tuple[IndicatorSpec, ...]:
    return tuple(spec for spec in INDICATORS.values() if spec.source is source)
