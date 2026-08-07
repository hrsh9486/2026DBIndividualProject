"""Final allocation, delivery, production, private and corporate JSON builders."""

from __future__ import annotations

from datetime import date, datetime, timezone

from builders.dated_multi_series import (
    build_dated_multi_series_payload,
    metric_source_rows,
    select_metric_records,
    structural_definitions,
)
from config.capex_structural import get_capex_structural_bundle
from models.capex_metrics import PrivateMetrics
from models.capex_sources import AnnualSourceDataset, AnnualSourceSeries
from transforms.corporate_fundamentals import build_corporate_fundamentals_payload
from validators import validate_dated_payload_quality


PRIVATE_KEYS = (
    "private_corporate_gfcf_pct_gdp",
    "private_share_total_gfcf",
    "manufacturing_capacity_utilisation",
    "public_capex_lagged",
)


def _series_by_key(dataset: AnnualSourceDataset, key: str) -> AnnualSourceSeries:
    for series in dataset.series:
        if series.key == key:
            return series
    raise KeyError(f"Source dataset {dataset.key!r} has no series {key!r}")


def _values(series: AnnualSourceSeries) -> list[dict]:
    values = []
    for observation in series.observations:
        start_year = int(observation.fiscal_period[:4])
        values.append({
            "date": f"{start_year + 1}-03-31",
            "period_label": f"FY{observation.fiscal_period}",
            "value": observation.value,
            "status": observation.status,
        })
    return values


def _references(dataset: AnnualSourceDataset) -> list[dict]:
    return [
        {
            "name": reference.name,
            "url": reference.url,
            "retrieved_at": reference.retrieved_at,
        }
        for reference in dataset.references
    ]


def _date_bounds(dataset: AnnualSourceDataset) -> tuple[str, str]:
    dates = []
    for series in dataset.series:
        for observation in series.observations:
            dates.append(f"{int(observation.fiscal_period[:4]) + 1}-03-31")
    if not dates:
        raise ValueError(f"Source dataset {dataset.key!r} contains no observations")
    return min(dates), max(dates)


def build_allocation_payload(source: AnnualSourceDataset) -> dict:
    railways = _series_by_key(source, "railways_budget_capex")
    roads = _series_by_key(source, "roads_budget_capex")
    series = {
        "railways_budget_capex": {
            "label": "Railways central budget CapEx",
            "entity": "IND",
            "unit": "INR_crore",
            "is_derived": False,
            "methodology": "Budget estimate of central budgetary support/capital expenditure for the Ministry of Railways.",
            "source_note": "Excludes internal and extra-budgetary resources; budget allocations are plans, not actual expenditure.",
            "values": _values(railways),
        },
        "roads_budget_capex": {
            "label": "Roads central budget CapEx",
            "entity": "IND",
            "unit": "INR_crore",
            "is_derived": False,
            "methodology": "Budget estimate of capital expenditure for the Ministry of Road Transport and Highways.",
            "source_note": "Budget allocations are plans, not actual expenditure.",
            "values": _values(roads),
        },
    }
    start_date, end_date = _date_bounds(source)
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": _references(source),
            "frequency": "annual",
            "start_date": start_date,
            "end_date": end_date,
            "indicator_code": "CAPEX_SECTOR_ALLOCATION",
            "label": "Roads and railways central-budget CapEx",
            "default_unit": "INR_crore",
            "series_order": list(series),
            "is_derived": False,
            "methodology": "Like-for-like central-budget allocations; Railways' internal and extra-budgetary resources are excluded.",
            "note": "Budget allocations are financial inputs, not evidence that projects were completed.",
        },
        "series": series,
    }


def build_delivery_payload(source: AnnualSourceDataset) -> dict:
    highways = _series_by_key(source, "national_highways_constructed_km")
    railways = _series_by_key(source, "railway_route_km_electrified")
    series = {
        "national_highways_constructed_km": {
            "label": "National highways constructed",
            "entity": "IND",
            "unit": "kilometres",
            "is_derived": False,
            "methodology": "National-highway construction completed during the fiscal year.",
            "source_note": "Kilometres do not adjust for lane width, project complexity, quality or maintenance.",
            "values": _values(highways),
        },
        "railway_route_km_electrified": {
            "label": "Railway route electrified",
            "entity": "IND",
            "unit": "route_kilometres",
            "is_derived": False,
            "methodology": "Broad-gauge railway route kilometres electrified during the fiscal year.",
            "source_note": "Electrification is one railway output; it does not measure new track, capacity added or service quality.",
            "values": _values(railways),
        },
    }
    start_date, end_date = _date_bounds(source)
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": _references(source),
            "frequency": "annual",
            "start_date": start_date,
            "end_date": end_date,
            "indicator_code": "CAPEX_PHYSICAL_DELIVERY",
            "label": "Roads and railways physical delivery",
            "default_unit": "kilometres",
            "series_order": list(series),
            "is_derived": False,
            "methodology": "Published fiscal-year physical outputs, measured in kilometres.",
            "note": "These output measures establish delivery, not economic additionality or a causal return on each rupee spent.",
        },
        "series": series,
    }


def build_production_payload(source: AnnualSourceDataset) -> dict:
    production = _series_by_key(source, "capital_goods_iip")
    series = {
        "capital_goods_iip": {
            "label": "Capital-goods production",
            "entity": "IND",
            "unit": "index",
            "is_derived": False,
            "methodology": "Fiscal-year average IIP for capital goods, use-based classification, base 2011-12=100.",
            "source_note": "Capital-goods IIP is volatile and measures output, not orders, profitability or private ownership of investment.",
            "values": _values(production),
        }
    }
    start_date, end_date = _date_bounds(source)
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": _references(source),
            "frequency": "annual",
            "start_date": start_date,
            "end_date": end_date,
            "indicator_code": "CAPITAL_GOODS_IIP",
            "label": "Capital-goods industrial production",
            "default_unit": "index",
            "series_order": list(series),
            "is_derived": False,
            "methodology": "Published fiscal-year average; no rebasing or interpolation.",
            "note": "The pandemic discontinuity is retained. Use the series as a real-output check, not as proof that public CapEx caused production.",
        },
        "series": series,
    }


def build_private_response_payload(private: PrivateMetrics) -> dict:
    """Build private-investment-response.json from PrivateMetrics."""
    bundle = get_capex_structural_bundle("private_investment")
    payload = build_dated_multi_series_payload(
        select_metric_records(private.records, PRIVATE_KEYS, date(2018, 3, 31)),
        structural_definitions(bundle, PRIVATE_KEYS),
        indicator_code="PRIVATE_INVESTMENT_CROWDING_IN",
        label=bundle.label,
        frequency=bundle.frequency,
        sources=metric_source_rows(private.sources),
        methodology=(
            "Private corporate means private non-financial plus private financial "
            "corporations under the 2022-23 national-accounts base. The public-CapEx "
            "series is shifted forward one fiscal year. Capacity utilisation is RBI "
            "OBICUS' published unadjusted aggregate."
        ),
        note=bundle.limitation,
    )
    validate_dated_payload_quality(
        payload,
        required_non_empty=PRIVATE_KEYS,
        bounds={
            "private_corporate_gfcf_pct_gdp": (0, 100),
            "private_share_total_gfcf": (0, 100),
            "public_capex_lagged": (0, 100),
            "manufacturing_capacity_utilisation": (0, 100),
        },
    )
    return payload


def build_corporate_payload(corporate_records: tuple) -> dict:
    """Build corporate-fundamentals.json from typed company observations."""
    return build_corporate_fundamentals_payload(corporate_records)
