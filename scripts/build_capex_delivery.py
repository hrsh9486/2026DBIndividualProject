"""Build the sector-allocation, physical-delivery and capital-goods IIP layers."""

from __future__ import annotations

from datetime import datetime, timezone

from config import PROCESSED_DATA_DIR
from config.capex_analysis import OUTPUTS
from exporters import publish_json


RETRIEVED_AT = "2026-07-30T00:00:00+00:00"

# Central budgetary support/capital expenditure, not Railways' wider capital
# outlay (which also includes internal and extra-budgetary resources).
ALLOCATIONS = {
    "railways_budget_capex": {
        "2018-19": 53060,
        "2019-20": 65837,
        "2020-21": 70000,
        "2021-22": 107100,
        "2022-23": 137100,
        "2023-24": 240000,
        "2024-25": 252000,
        "2025-26": 252000,
    },
    "roads_budget_capex": {
        "2018-19": 59440.25,
        "2019-20": 72058.58,
        "2020-21": 81974.71,
        "2021-22": 108230.11,
        "2022-23": 187744,
        "2023-24": 258605.53,
        "2024-25": 272241.15,
        "2025-26": 272241.15,
    },
}

# The latest ministry reports reproduce the historical series on one chart,
# avoiding accidental comparisons between targets and achievements.
DELIVERY = {
    "national_highways_constructed_km": {
        "2018-19": 10855,
        "2019-20": 10237,
        "2020-21": 13327,
        "2021-22": 10457,
        "2022-23": 10331,
        "2023-24": 12349,
    },
    "railway_route_km_electrified": {
        "2018-19": 5276,
        "2019-20": 4378,
        "2020-21": 6015,
        "2021-22": 6366,
        "2022-23": 6565,
        "2023-24": 4644,
    },
}

IIP = {
    "2014-15": 95.5,
    "2015-16": 98.4,
    "2016-17": 101.5,
    "2017-18": 105.6,
    "2018-19": 108.4,
    "2019-20": 93.3,
    "2020-21": 75.9,
    "2021-22": 88.7,
    "2022-23": 100.3,
}


def _values(rows: dict[str, float], *, status: str = "actual") -> list[dict]:
    return [
        {
            "date": f"{int(period[:4]) + 1}-03-31",
            "period_label": f"FY{period}",
            "value": value,
            "status": status,
        }
        for period, value in rows.items()
    ]


def build_allocation_payload() -> dict:
    series = {
        "railways_budget_capex": {
            "label": "Railways central budget CapEx",
            "entity": "IND",
            "unit": "INR_crore",
            "is_derived": False,
            "methodology": "Budget estimate of central budgetary support/capital expenditure for the Ministry of Railways.",
            "source_note": "Excludes internal and extra-budgetary resources; budget allocations are plans, not actual expenditure.",
            "values": _values(ALLOCATIONS["railways_budget_capex"], status="budget"),
        },
        "roads_budget_capex": {
            "label": "Roads central budget CapEx",
            "entity": "IND",
            "unit": "INR_crore",
            "is_derived": False,
            "methodology": "Budget estimate of capital expenditure for the Ministry of Road Transport and Highways.",
            "source_note": "Budget allocations are plans, not actual expenditure.",
            "values": _values(ALLOCATIONS["roads_budget_capex"], status="budget"),
        },
    }
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [
                {
                    "name": "Union Budget 2019-20 — Expenditure Profile, Statement 3",
                    "url": "https://www.indiabudget.gov.in/budget2019-20/doc/eb/stat3a.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
                {
                    "name": "Union Budget 2021-22 — Expenditure Profile, Statement 3",
                    "url": "https://www.indiabudget.gov.in/budget2021-22/doc/eb/stat3a.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
                {
                    "name": "Union Budget 2023-24 — Expenditure Profile, Statement 3",
                    "url": "https://www.indiabudget.gov.in/budget2023-24/doc/eb/stat3a.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
                {
                    "name": "Union Budget 2025-26 — Expenditure Profile, Statement 3",
                    "url": "https://www.indiabudget.gov.in/budget2025-26/doc/eb/vol1.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
            ],
            "frequency": "annual",
            "start_date": "2019-03-31",
            "end_date": "2026-03-31",
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


def build_delivery_payload() -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    series = {
        "national_highways_constructed_km": {
            "label": "National highways constructed",
            "entity": "IND",
            "unit": "kilometres",
            "is_derived": False,
            "methodology": "National-highway construction completed during the fiscal year.",
            "source_note": "Kilometres do not adjust for lane width, project complexity, quality or maintenance.",
            "values": _values(DELIVERY["national_highways_constructed_km"]),
        },
        "railway_route_km_electrified": {
            "label": "Railway route electrified",
            "entity": "IND",
            "unit": "route_kilometres",
            "is_derived": False,
            "methodology": "Broad-gauge railway route kilometres electrified during the fiscal year.",
            "source_note": "Electrification is one railway output; it does not measure new track, capacity added or service quality.",
            "values": _values(DELIVERY["railway_route_km_electrified"]),
        },
    }
    return {
        "metadata": {
            "generated_at": generated_at,
            "source": [
                {
                    "name": "MoRTH Annual Report 2024-25 — year-wise NH construction",
                    "url": "https://morth.nic.in/sites/default/files/Annual-Report-English-with-Cover.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
                {
                    "name": "Indian Railways Annual Report and Accounts 2023-24",
                    "url": "https://indianrailways.gov.in/railwayboard/uploads/directorate/stat_econ/2025/Indian%20Railways%20Annual%20Report%20%20Accounts%202023-24%20-English.pdf",
                    "retrieved_at": RETRIEVED_AT,
                },
            ],
            "frequency": "annual",
            "start_date": "2019-03-31",
            "end_date": "2024-03-31",
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


def build_production_payload() -> dict:
    series = {
        "capital_goods_iip": {
            "label": "Capital-goods production",
            "entity": "IND",
            "unit": "index",
            "is_derived": False,
            "methodology": "Fiscal-year average IIP for capital goods, use-based classification, base 2011-12=100.",
            "source_note": "Capital-goods IIP is volatile and measures output, not orders, profitability or private ownership of investment.",
            "values": _values(IIP),
        }
    }
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": [{
                "name": "RBI Handbook of Statistics on the Indian Economy, Table 30 (source: NSO)",
                "url": "https://rbi.org.in/scripts/PublicationsView.aspx?id=21836",
                "retrieved_at": RETRIEVED_AT,
            }],
            "frequency": "annual",
            "start_date": "2015-03-31",
            "end_date": "2023-03-31",
            "indicator_code": "CAPITAL_GOODS_IIP",
            "label": "Capital-goods industrial production",
            "default_unit": "index",
            "series_order": ["capital_goods_iip"],
            "is_derived": False,
            "methodology": "Published fiscal-year average; no rebasing or interpolation.",
            "note": "The pandemic discontinuity is retained. Use the series as a real-output check, not as proof that public CapEx caused production.",
        },
        "series": series,
    }


def main() -> None:
    publish_json(
        build_allocation_payload(),
        PROCESSED_DATA_DIR / OUTPUTS["allocation"],
        "dated_multi_series.schema.json",
    )
    publish_json(
        build_delivery_payload(),
        PROCESSED_DATA_DIR / OUTPUTS["delivery"],
        "dated_multi_series.schema.json",
    )
    publish_json(
        build_production_payload(),
        PROCESSED_DATA_DIR / OUTPUTS["production"],
        "dated_multi_series.schema.json",
    )


if __name__ == "__main__":
    main()
